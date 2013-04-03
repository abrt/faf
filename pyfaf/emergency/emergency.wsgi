#! /usr/bin/env python

import os
import cgi
import json
import uuid
import logging

from wsgiref.simple_server import make_server

import pyfaf


def application(environ, start_response):
    """
    WSGI application capable of saving incoming uReports to
    directory, to be used as a backup handler.
    """

    def is_post_request(environ):
        """
        Return True if this request is valid POST request
        with correct content type
        """

        if environ["REQUEST_METHOD"].upper() != "POST":
            return False

        content_type = environ.get("CONTENT_TYPE", "application/x-www-form-urlencoded")
        return content_type.startswith("multipart/form-data")

    def bad_request():
        """
        Respond with HTTP 400 Bad Reqeust.
        """

        start_response("400 BAD REQUEST",
                       [("Content-Type", "application/json")])
        return [""]

    def method_not_allowed():
        """
        Respond with HTTP 405 Method Not Allowed.
        """

        start_response("405 METHOD NOT ALLOWED",
                       [("Content-Type", "application/json"),
                       ("Allow", "POST")])
        return [""]

    spool_dir = pyfaf.config.get("Report.SpoolDirectory")

    if not is_post_request(environ):
        logging.debug('Not a POST request or content type'
                      ' is not mulitpart/form-data.')

        return method_not_allowed()

    inp = environ["wsgi.input"]
    fs = cgi.FieldStorage(fp=inp, environ=environ)

    try:
        fs = fs.list.pop()
        ureport = fs.file.read()
    except (IndexError, AttributeError):
        logging.debug('Unable to parse input.')
        return bad_request()

    fname = str(uuid.uuid4())
    with open(os.path.join(spool_dir, "incoming", fname), "w") as fil:
        fil.write(ureport)
        logging.info('Report saved as {0}'.format(fname))

    status = "202 ACCEPTED"
    response_body = json.dumps({"result": False})
    response_headers = [("Content-Type", "application/json"),
                        ("Content-Length", str(len(response_body)))]
    start_response(status, response_headers)

    return [response_body]

if __name__ == "__main__":
    # possible to run as standalone server,
    # mainly for debugging purposes

    logging.basicConfig(level=logging.DEBUG)
    server = make_server("0.0.0.0", 8000, application)
    server.serve_forever()
