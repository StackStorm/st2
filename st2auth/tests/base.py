from webtest import TestApp

import tests.config
from st2tests import DbTestCase
from st2auth import app


class FunctionalTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(FunctionalTest, cls).setUpClass()
        tests.config.parse_args()
        cls.app = TestApp(app.setup_app())

    @classmethod
    def tearDownClass(cls):
        super(FunctionalTest, cls).tearDownClass()
