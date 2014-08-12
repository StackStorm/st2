import sys
import eventlet
import st2tests.config

from unittest2 import TestCase
from oslo.config import cfg
from st2common.models.db import db_setup, db_teardown


class EventletTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        eventlet.monkey_patch(
            os=True,
            select=True,
            socket=True,
            thread=False if '--use-debugger' in sys.argv else True,
            time=True
        )

    @classmethod
    def tearDownClass(cls):
        eventlet.monkey_patch(
            os=False,
            select=False,
            socket=False,
            thread=False,
            time=False
        )


class DbTestCase(TestCase):

    db_connection = None

    @classmethod
    def setUpClass(cls):
        st2tests.config.parse_args()
        DbTestCase.db_connection = db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host,
                                            cfg.CONF.database.port)

    @classmethod
    def tearDownClass(cls):
        DbTestCase.db_connection.drop_database(cfg.CONF.database.db_name)
        db_teardown()
        DbTestCase.db_connection = None
