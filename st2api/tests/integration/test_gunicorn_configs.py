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

import os
import random
import httplib

import unittest2
import requests
import eventlet
from eventlet.green import subprocess

from st2common.models.utils import profiling
from st2common.util.shell import kill_process
from st2tests.base import IntegrationTestCase


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ST2_CONFIG_PATH = os.path.join(BASE_DIR, '../../../conf/st2.tests.conf')


class GunicornWSGIEntryPointTestCase(IntegrationTestCase):
    @unittest2.skipIf(profiling.is_enabled(), 'Profiling is enabled')
    def test_st2api_wsgi_entry_point(self):
        port = random.randint(10000, 30000)
        config_path = os.path.join(BASE_DIR, '../../../st2api/st2api/gunicorn_config.py')
        cmd = ('gunicorn_pecan %s -k eventlet -w 1 -b 127.0.0.1:%s' % (config_path, port))
        env = os.environ.copy()
        env['ST2_CONFIG_PATH'] = ST2_CONFIG_PATH
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                                   shell=True, preexec_fn=os.setsid)
        self.add_process(process=process)
        eventlet.sleep(5)
        self.assertProcessIsRunning(process=process)
        response = requests.get('http://127.0.0.1:%s/v1/actions' % (port))
        self.assertEqual(response.status_code, httplib.OK)
        kill_process(process)

    @unittest2.skipIf(profiling.is_enabled(), 'Profiling is enabled')
    def test_st2auth(self):
        port = random.randint(10000, 30000)
        config_path = os.path.join(BASE_DIR, '../../../st2auth/st2auth/gunicorn_config.py')
        cmd = ('gunicorn_pecan %s -k eventlet -w 1 -b 127.0.0.1:%s' % (config_path, port))
        env = os.environ.copy()
        env['ST2_CONFIG_PATH'] = ST2_CONFIG_PATH
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                                   shell=True, preexec_fn=os.setsid)

        self.add_process(process=process)
        eventlet.sleep(5)
        self.assertProcessIsRunning(process=process)
        response = requests.post('http://127.0.0.1:%s/tokens' % (port))
        self.assertEqual(response.status_code, httplib.UNAUTHORIZED)
        kill_process(process)
