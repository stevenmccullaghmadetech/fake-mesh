#!/usr/bin/env python
from __future__ import absolute_import, print_function

import argparse
import logging
import logging.handlers
import os
import signal
import ssl

from cheroot.wsgi import Server
from cheroot.ssl.builtin import BuiltinSSLAdapter

from .wsgi_app import FakeMeshApplication
from .wsgi_helpers import DebugMiddleware, LoggingMiddleware


_data_dir = os.path.dirname(__file__)
default_ca_cert = os.path.join(_data_dir, "ca.cert.pem")
default_server_cert = os.path.join(_data_dir, "server.cert.pem")
default_server_key = os.path.join(_data_dir, "server.key.pem")


LOGGER_NAME = 'fake_mesh'


def make_server(db_dir='/tmp/fake_mesh_dir',
                host='0.0.0.0',
                port=8829,
                ca_cert=default_ca_cert,
                server_cert=default_server_cert,
                server_key=default_server_key,
                debug=False, logging=False):
    app = FakeMeshApplication(db_dir)
    if debug:
        app = DebugMiddleware(app)
    elif logging:
        app = LoggingMiddleware(app, logger=LOGGER_NAME)
    httpd = Server((host, port), app)

    server_context = ssl.create_default_context(
        ssl.Purpose.CLIENT_AUTH, cafile=ca_cert)
    server_context.load_cert_chain(server_cert, server_key)
    server_context.check_hostname = False
    server_context.verify_mode = ssl.CERT_REQUIRED

    ssl_adapter = BuiltinSSLAdapter(server_cert, server_key, ca_cert)
    ssl_adapter.context = server_context
    httpd.ssl_adapter = ssl_adapter

    return httpd


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Run a fake MESH server"
    )
    parser.add_argument(
        '--dir', default='/tmp/fake_mesh_dir',
        help="Where to store the application data")
    parser.add_argument(
        '--ca-cert', default=default_ca_cert,
        help='CA certificate to validate incoming connections against'
    )
    parser.add_argument(
        '--cert', default=default_server_cert,
        help='SSL certificate for this server'
    )
    parser.add_argument(
        '--key', default=default_server_key,
        help='SSL private key for this server'
    )
    parser.add_argument(
        '-p', '--port', default=8829, type=int, help="Port to listen on")
    parser.add_argument(
        '-i', '--host', default='0.0.0.0', help="Host interface to bind to")
    parser.add_argument(
        '-d', '--debug', action='store_true',
        help="Print data sent and received to stderr")
    parser.add_argument(
        '--no-log', action='store_true', help="Disable all logging")
    parser.add_argument(
        '--log-file', nargs='?',
        help="File to use for logging - use stderr if not specified")
    args = parser.parse_args()

    httpd = make_server(args.dir, args.host, args.port, args.ca_cert,
                        args.cert, args.key, args.debug, not args.no_log)

    if not args.no_log:
        logger = logging.getLogger(LOGGER_NAME)
        logger.setLevel(logging.INFO)
        if args.log_file:
            logger.addHandler(
                logging.handlers.WatchedFileHandler(args.log_file))
        else:
            logger.addHandler(logging.StreamHandler())
        logger.info('Running Fake Mesh on %s:%s', args.host, args.port)

    def shutdown_handler(signal, frame):
        httpd.stop()
    signal.signal(signal.SIGTERM, shutdown_handler)

    httpd.safe_start()
