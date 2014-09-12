from pecan.testing import load_test_app

import tests.config
from st2tests import DbTestCase


class FunctionalTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(FunctionalTest, cls).setUpClass()

        tests.config.parse_args()

        config = {
            'app': {
                'root': 'st2auth.controllers.root.RootController',
                'modules': ['st2auth'],
                'debug': True,
                'errors': {'__force_dict__': True}
            }
        }

        cls.app = load_test_app(config=config)

    @classmethod
    def tearDownClass(cls):
        super(FunctionalTest, cls).tearDownClass()
