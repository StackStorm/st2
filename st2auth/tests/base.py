from webtest import TestApp

from st2tests import DbTestCase
from st2auth import app
import st2tests.config as tests_config


class FunctionalTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(FunctionalTest, cls).setUpClass()
        tests_config.parse_args()
        cls.app = TestApp(app.setup_app())

    @classmethod
    def tearDownClass(cls):
        super(FunctionalTest, cls).tearDownClass()
