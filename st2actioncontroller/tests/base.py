import tests.config
from pecan.testing import load_test_app
from unittest import TestCase
from oslo.config import cfg
from st2common.models.db import db_setup, db_teardown


class FunctionalTest(TestCase):

    db_connection = None

    @classmethod
    def setUpClass(cls):
        tests.config.parse_args()
        FunctionalTest.db_connection = db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host,
                                                cfg.CONF.database.port)

        opts = cfg.CONF.action_controller_pecan
        cfg_dict = {
            'app': {
                'root': opts.root,
                'template_path': opts.template_path,
                'modules': opts.modules,
                'debug': opts.debug,
                'auth_enable': opts.auth_enable,
                'errors': {404: '/error/404', '__force_dict__': True}
            }
        }
        cls.app = load_test_app(config=cfg_dict)

    @classmethod
    def tearDownClass(cls):
        FunctionalTest.__do_db_teardown()

    @staticmethod
    def __do_db_teardown():
        FunctionalTest.db_connection.drop_database(cfg.CONF.database.db_name)
        db_teardown()
