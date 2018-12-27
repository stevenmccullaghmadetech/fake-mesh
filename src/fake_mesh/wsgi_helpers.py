from __future__ import print_function

import logging
import sys


from wsgiref.headers import Headers
from wsgiref.util import request_uri


class DebugMiddleware(object):
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
                print(result.decode('iso-8859-1', 'replace'), file=sys.stderr)
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
            sys.stderr.write(data.decode('iso-8859-1', 'replace'))
            yield data
        print(file=sys.stderr)


class LoggingMiddleware(object):
    def __init__(self, app, logger='wsgi_request'):
        self._app = app
        self._logger = logging.getLogger(logger)

    def __call__(self, environ, start_response):
        method = environ['REQUEST_METHOD']
        uri = request_uri(environ)

        def inner_start_response(status, headers, exc_info=None):
            inner_start_response.status = status
            if exc_info is None:
                return start_response(status, headers)
            else:
                return start_response(status, headers, exc_info)

        result = self._app(environ, inner_start_response)
        self._logger.info("%s %s -> %s",
                          method, uri, inner_start_response.status)
        return result
