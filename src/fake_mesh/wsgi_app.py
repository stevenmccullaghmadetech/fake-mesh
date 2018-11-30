import collections
import datetime
import hmac
import json
import lmdb
import monotonic
import os
import random
import tempfile
import time
import traceback
import wrapt
import zlib

from hashlib import sha256
from werkzeug.wrappers import Request, Response
from werkzeug.wsgi import pop_path_info, responder, wrap_file, \
                          get_input_stream, DispatcherMiddleware
from wsgiref.headers import Headers

try:
    import cPickle as pickle
except ImportError:
    import pickle


IO_BLOCK_SIZE = 65536


TIMESTAMP_FORMAT = '%Y%m%d%H%M%S%f'


BadRequest = Response("Bad Request", status=400)
NotAuthorized = Response("Unauthorized", status=401)
Forbidden = Response("Forbidden", status=403)
NotFound = Response('Not Found', status=404)
ServerError = Response("Server Error", status=500)


_OPTIONAL_HEADERS = {
    "HTTP_CONTENT_ENCODING": "Content-Encoding",
    "HTTP_MEX_WORKFLOWID": "Mex-WorkflowID",
    "HTTP_MEX_FILENAME": "Mex-FileName",
    "HTTP_MEX_LOCALID": "Mex-LocalID",
    "HTTP_MEX_MESSAGETYPE": "Mex-MessageType",
    "HTTP_MEX_PROCESSID": "Mex-ProcessID",
    "HTTP_MEX_SUBJECT": "Mex-Subject",
    "HTTP_MEX_ENCRYPTED": "Mex-Encrypted",
    "HTTP_MEX_COMPRESS": "Mex-Compress",
    "HTTP_MEX_COMPRESSED": "Mex-Compressed",
    "HTTP_MEX_CHUNK_RANGE": "Mex-Chunk-Range",
    "HTTP_MEX_FROM": "Mex-From",
    "HTTP_MEX_TO": "Mex-To",
}


def expectation_failed(message):
    return Response(json.dumps({
        "errorCode": "02",
        "errorDescription": str(message),
        "errorEvent": "COLLECT",
        "messageID": "99999"
    }), status=417, content_type='application/json')


def decompress_file(f):
    with f:
        decompressor = zlib.decompressobj(31)
        while True:
            data = f.read(IO_BLOCK_SIZE)
            if data:
                yield decompressor.decompress(data)
            else:
                yield decompressor.flush()
                break


class MonotonicTimestampSource(object):
    def __init__(self):
        self._ts_minus_monotonic = (
            datetime.datetime.utcnow()
            - datetime.timedelta(seconds=monotonic.monotonic())
        )

    def __call__(self):
        return (
            self._ts_minus_monotonic
            + datetime.timedelta(seconds=monotonic.monotonic())
        )


Metadata = collections.namedtuple('Metadata', ['chunks', 'recipient', 'extra_headers', 'all_chunks_received'])


class FakeMeshApplication(object):
    def __init__(self, storage_dir=None, shared_key=b"BackBone"):
        self._shared_key = shared_key
        if not storage_dir:
            storage_dir = tempfile.mkdtemp()
        self.file_dir = os.path.join(storage_dir, 'storage')
        try:
            os.makedirs(self.file_dir)
        except:
            pass  # This is OK

        self.db_env = lmdb.Environment(
            os.path.join(storage_dir, 'db'),
            map_size=1024**3,  # 1GB - mostly metadata, so should be fine
            max_dbs=4
        )
        self.nonce_db = self.db_env.open_db(b'nonce')
        self.inbox_db = self.db_env.open_db(b'inbox', dupsort=True)
        self.metadata_db = self.db_env.open_db(b'metadata')
        self.increment_db = self.db_env.open_db(b'increment')

        self.timestamp_source = MonotonicTimestampSource()

    def __call__(self, environ, start_response):
        return DispatcherMiddleware(
            NotFound, {
                '/messageexchange': self.authenticated(
                    DispatcherMiddleware(
                        self.handshake, {
                            '/inbox': self.inbox,
                            '/count': self.count,
                            '/outbox': self.outbox,
                            '/update': self.update
                        }
                    )
                )
            }
        )(environ, start_response)

    @wrapt.decorator
    def authenticated(self, wrapped, instance, args, kwargs):
        environ, start_response = args
        requested_mailbox = pop_path_info(environ)
        auth_data = environ.get("HTTP_AUTHORIZATION", "")
        if not auth_data:
            return NotAuthorized(environ, start_response)

        if auth_data.startswith("NHSMESH "):
            auth_data = auth_data[8:]

        mailbox, nonce, nonce_count, ts, hashed = auth_data.split(":")
        expected_password = "password"
        hash_data = ":".join([
            mailbox, nonce, nonce_count, expected_password, ts
        ])
        myhash = hmac.HMAC(self._shared_key, hash_data.encode("ascii"),
                           sha256).hexdigest()

        with self.db_env.begin(self.nonce_db, write=True) as auth_tx:
            nonce_value = ':'.join([mailbox, nonce, nonce_count]).encode('ascii')
            nonce_used = auth_tx.get(nonce_value) is not None
            auth_tx.put(nonce_value, b'1')
        if myhash == hashed and mailbox == requested_mailbox and not nonce_used:
            environ["mesh.mailbox"] = mailbox
            return wrapped(environ, start_response)
        else:
            return Forbidden(environ, start_response)

    @Request.application
    def handshake(self, request):
        for header in ['Mex-ClientVersion', 'Mex-JavaVersion',
                       'Mex-OSArchitecture', 'Mex-OSName', 'Mex-OSVersion']:
            assert header in request.headers
        return Response('OK')

    @Request.application
    def update(self, request):
        return Response('', '204 No Content', {'Mex-Client-Update-Available': ''})

    @responder
    def inbox(self, environ, start_response):
        request_method = environ["REQUEST_METHOD"]
        message_id = pop_path_info(environ)
        mailbox = environ["mesh.mailbox"]

        if (request_method == "PUT" and
                environ["PATH_INFO"] == "/status/acknowledged"):
            self.delete_message(mailbox, message_id)
            return Response('OK')

        if request_method == "GET":
            if message_id:
                chunk_num = pop_path_info(environ) or 1
                return self.download_chunk(mailbox, message_id, chunk_num)
            else:
                messages = {"messages": list(self.list_messages(mailbox))}
                return Response(json.dumps(messages),
                                content_type='application/json')
        else:
            return BadRequest

    @responder
    def count(self, environ, start_response):
        if environ["REQUEST_METHOD"] == "GET":
            count = sum(1 for _ in self.list_messages(environ["mesh.mailbox"]))
            response = {
                "count": count,
                "internalID": "{ts}_{rand:06d}_{ts2}".format(
                    ts=datetime.datetime.utcnow().strftime(TIMESTAMP_FORMAT),
                    rand=random.randint(0, 999999),
                    ts2=int(time.time())
                ),
                "allResultsIncluded": True
            }
            return Response(json.dumps(response),
                            content_type='application/json')
        else:
            return BadRequest

    @responder
    def outbox(self, environ, start_response):
        mailbox_id = environ["mesh.mailbox"]
        message_id = pop_path_info(environ)
        if message_id:
            chunk_num = pop_path_info(environ)
            with self.db_env.begin(db=self.metadata_db) as tx:
                metadata = pickle.loads(tx.get(message_id.encode('ascii')))
            self.save_chunk(environ, metadata.recipient, message_id, chunk_num)
            if int(chunk_num) == metadata.chunks:
                metadata = metadata._replace(all_chunks_received=True)
                with self.db_env.begin(db=self.metadata_db, write=True) as tx:
                    tx.put(message_id.encode('ascii'), pickle.dumps(metadata))
            return Response('', status=202)
        else:
            try:
                recipient = environ["HTTP_MEX_TO"]
                sender = environ["HTTP_MEX_FROM"]
                assert mailbox_id == sender
            except Exception as e:
                traceback.print_exc()
                return expectation_failed(e)

            message_id = self._new_message_id()
            self.save_chunk(environ, recipient, message_id, 1)

            headers = {_OPTIONAL_HEADERS[key]: value
                       for key, value in environ.items()
                       if key in _OPTIONAL_HEADERS}
            chunk_header = environ.get('HTTP_MEX_CHUNK_RANGE', '1:1')
            chunk_count = int(chunk_header.rsplit(':', 1)[1])
            metadata = Metadata(chunk_count, recipient, headers, chunk_count == 1)

            with self.db_env.begin(write=True) as tx:
                tx.put(message_id.encode('ascii'),
                       pickle.dumps(metadata),
                       db=self.metadata_db)
                tx.put(recipient.encode('ascii'),
                       message_id.encode('ascii'),
                       dupdata=True,
                       db=self.inbox_db)

            message = json.dumps({'messageID': message_id})
            return Response(message, status=202)

    def save_chunk(self, environ, mailbox, message_id, chunk_num):
        instream = get_input_stream(environ, safe_fallback=False)
        filename = self.get_filename(mailbox, message_id, chunk_num)
        with open(filename, 'wb') as f:
            if environ.get('HTTP_CONTENT_ENCODING') == 'gzip':
                while True:
                    data = instream.read(IO_BLOCK_SIZE)
                    if data:
                        f.write(data)
                    else:
                        break
            else:
                compressor = zlib.compressobj(9, zlib.DEFLATED, 31)
                while True:
                    data = instream.read(IO_BLOCK_SIZE)
                    if data:
                        f.write(compressor.compress(data))
                    else:
                        f.write(compressor.flush(zlib.Z_FINISH))
                        break

    def download_chunk(self, mailbox, message_id, chunk_num):
        chunk_num = int(chunk_num)

        def handle(environ, start_response):
            with self.db_env.begin(self.metadata_db) as tx:
                message = pickle.loads(tx.get(message_id.encode('ascii')))
            assert message.recipient == mailbox
            status = '206 Partial Content' if message.chunks > chunk_num else '200 OK'
            chunk_header = "{}:{}".format(chunk_num, message.chunks)
            headers = Headers([
                ('Content-Type', 'application/octet-stream'),
                ('Mex-Chunk-Range', chunk_header),
                ('Mex-MessageID', str(message_id))
            ])
            for k, v in message.extra_headers.items():
                headers[k] = v

            f = open(self.get_filename(mailbox, message_id, chunk_num), 'rb')
            if "gzip" in environ.get('HTTP_ACCEPT_ENCODING', ''):
                headers['Content-Encoding'] = 'gzip'
                start_response(status, headers.items())
                return wrap_file(environ, f)
            else:

                start_response(status, headers.items())
                return decompress_file(f)

        return handle

    def _new_message_id(self):
        with self.db_env.begin(self.increment_db, write=True) as tx:
            message_num = int(tx.get(b'increment', b'0'))
            tx.put(b'increment', str(message_num + 1).encode('ascii'))
            ts = self.timestamp_source().strftime(TIMESTAMP_FORMAT)
            return "{ts}_{num:09d}".format(ts=ts, num=message_num)

    def list_messages(self, mailbox_id):
        with self.db_env.begin(self.inbox_db) as tx, tx.cursor() as cursor:
            if cursor.set_key(mailbox_id.encode('ascii')):
                for message_key in cursor.iternext_dup():
                    message = pickle.loads(
                        tx.get(message_key, db=self.metadata_db))
                    message_key = message_key.decode('ascii')
                    # Only list messages where all chunks received
                    if message.all_chunks_received:
                        yield message_key

    def delete_message(self, mailbox, message_id):
        message_key = message_id.encode('ascii')
        with self.db_env.begin(write=True) as tx:
            message = pickle.loads(tx.get(message_key, db=self.metadata_db))
            assert message.recipient == mailbox
            tx.delete(message_key, db=self.metadata_db)
            tx.delete(mailbox.encode('ascii'),
                      message_key, db=self.inbox_db)

            for i in range(1, message.chunks + 1):
                try:
                    os.remove(self.get_filename(mailbox, message_key, i))
                except IOError:
                    pass  # If it wasn't there, no biggie

    def get_filename(self, mailbox, message_id, chunk_num):
        return os.path.join(
            self.file_dir,
            '{}_{}_{}.dat'.format(mailbox, message_id, chunk_num)
        )
