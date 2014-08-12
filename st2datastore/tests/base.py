import tests.config
from pecan.testing import load_test_app
from oslo.config import cfg

from st2tests import DbTestCase


class FunctionalTest(DbTestCase):
    @classmethod
    def setUpClass(cls):
        super(FunctionalTest, cls).setUpClass()
        tests.config.parse_args()
        opts = cfg.CONF.datastore_pecan
        cfg_dict = {
            'app': {
                'root': opts.root,
                'template_path': opts.template_path,
                'modules': opts.modules,
                'debug': opts.debug,
                'auth_enable': opts.auth_enable,
                'errors': {'__force_dict__': True}
            }
        }
        cls.app = load_test_app(config=cfg_dict)

    @classmethod
    def tearDownClass(cls):
        super(FunctionalTest, cls).tearDownClass()
