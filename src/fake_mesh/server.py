#!/usr/bin/env python
from __future__ import absolute_import, print_function

import argparse
import os
import ssl
import sys

from cheroot.wsgi import Server
from cheroot.ssl.builtin import BuiltinSSLAdapter

from wsgiref.headers import Headers
from wsgiref.util import request_uri


from .wsgi_app import FakeMeshApplication


class DebugWsgi(object):
    def __init__(self, app):
        self._app = app

    def __call__(self, environ, start_response):
        request_line = environ['REQUEST_METHOD'] + ' ' + request_uri(environ)
        print(request_line, file=sys.stderr)
        if 'CONTENT_TYPE' in environ:
            print('Content-Type:', environ['CONTENT_TYPE'], file=sys.stderr)
        for k, v in environ.items():
            if k.startswith('HTTP_'):
                print(k[5:].lower().replace('_', '-') + ': ' + v,
                      file=sys.stderr)

        if 'wsgi.input' in environ:
            body = environ['wsgi.input']
            old_body_read = body.read

            def read(*args):
                result = old_body_read(*args)
                print(result, file=sys.stderr)
                return result

            body.read = read

        def inner_start_response(status, headers, exc_info=None):
            print(file=sys.stderr)
            print(status, file=sys.stderr)
            print(Headers(headers), file=sys.stderr)
            print(file=sys.stderr)
            if exc_info is None:
                return start_response(status, headers)
            else:
                return start_response(status, headers, exc_info)

        for data in self._app(environ, inner_start_response):
            sys.stderr.write(data)
            yield data
        print(file=sys.stderr)

if __name__ == '__main__':
    _data_dir = os.path.dirname(__file__)
    parser = argparse.ArgumentParser(
        description="Run a fake MESH server"
    )
    parser.add_argument(
        '--dir', default='/tmp/fake_mesh_dir',
        help="Where to store the application data")
    parser.add_argument(
        '--ca-cert', default=os.path.join(_data_dir, "ca.cert.pem"),
        help='CA certificate to validate incoming connections against'
    )
    parser.add_argument(
        '--cert', default=os.path.join(_data_dir, "server.cert.pem"),
        help='SSL certificate for this server'
    )
    parser.add_argument(
        '--key', default=os.path.join(_data_dir, "server.key.pem"),
        help='SSL private key for this server'
    )
    parser.add_argument(
        '-p', '--port', default=8829, help="Port to listen on")
    parser.add_argument(
        '-i', '--host', default='0.0.0.0', help="Host interface to bind to")
    parser.add_argument(
        '-d', '--debug', action='store_true',
        help="Print data sent and received to stderr")
    args = parser.parse_args()

    app = FakeMeshApplication(args.dir)
    if args.debug:
        app = DebugWsgi(app)
    httpd = Server((args.host, args.port), app)

    server_context = ssl.create_default_context(
        ssl.Purpose.CLIENT_AUTH, cafile=args.ca_cert)
    server_context.load_cert_chain(args.cert, args.key)
    server_context.check_hostname = False
    server_context.verify_mode = ssl.CERT_REQUIRED

    ssl_adapter = BuiltinSSLAdapter(args.cert, args.key, args.ca_cert)
    ssl_adapter.context = server_context
    httpd.ssl_adapter = ssl_adapter

    httpd.safe_start()
