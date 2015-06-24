# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pecan import load_app
from pecan.testing import load_test_app
from oslo_config import cfg
from webtest import TestApp


import st2actions.bootstrap.runnersregistrar as runners_registrar
from st2common.middleware import auth
from st2tests import DbTestCase
import st2tests.config as tests_config


class FunctionalTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(FunctionalTest, cls).setUpClass()

        tests_config.parse_args()
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
        tests_config.parse_args()

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
