#!/usr/bin/env python2.7

import eventlet

import os
import sys
from wsgiref import simple_server

from oslo.config import cfg

from st2common import log as logging

from st2actioncontroller.api import app
from st2actioncontroller import config

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)

LOG = logging.getLogger('mistral.cmd.api')


def main():
    try:
        config.parse_args()
        logging.setup('stactioncontroller')

        host = cfg.CONF.api.host
        port = cfg.CONF.api.port

        server = simple_server.make_server(host, port, app.setup_app())

        LOG.info("StactionController is serving on http://%s:%s (PID=%s)" %
                 (host, port, os.getpid()))

        server.serve_forever()
    except RuntimeError, e:
        sys.stderr.write("ERROR: %s\n" % e)
        sys.exit(1)


if __name__ == '__main__':
    main()
