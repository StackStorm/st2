from pecan import load_app
from pecan.testing import load_test_app
from oslo.config import cfg
from webtest import TestApp

import tests.config
from st2tests import DbTestCase
import st2actions.bootstrap.runnersregistrar as runners_registrar
from st2common.middleware import auth


class FunctionalTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(FunctionalTest, cls).setUpClass()

        tests.config.parse_args()
        cfg.CONF.set_default('enable', False, group='auth')

        opts = cfg.CONF.api_pecan
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

        # TODO(manas) : register action types here for now. RunnerType registration can be moved
        # to posting to /runnertypes but that implies implementing POST.
        runners_registrar.register_runner_types()

        cls.app = load_test_app(config=cfg_dict)


class AuthMiddlewareTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(AuthMiddlewareTest, cls).setUpClass()
        tests.config.parse_args()

        opts = cfg.CONF.api_pecan
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

        # TODO(manas) : register action types here for now. RunnerType registration can be moved
        # to posting to /runnertypes but that implies implementing POST.
        runners_registrar.register_runner_types()

        cls.app = TestApp(auth.AuthMiddleware(load_app(cfg_dict)))
