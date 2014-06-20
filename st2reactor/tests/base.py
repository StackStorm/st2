import tests.config
from unittest2 import TestCase
from oslo.config import cfg
from st2common.models.db import db_setup, db_teardown


class DbTestCase(TestCase):

    db_connection = None

    @classmethod
    def setUpClass(cls):
        tests.config.parse_args()
        DbTestCase.db_connection = db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host,
                                            cfg.CONF.database.port)

    @classmethod
    def tearDownClass(cls):
        DbTestCase.db_connection.drop_database(cfg.CONF.database.db_name)
        db_teardown()
