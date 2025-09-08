# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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

from six.moves import http_client
import requests
import eventlet
from eventlet.green import subprocess
import pytest

import st2tests.config
from st2common.models.utils import profiling
from st2common.util.shell import kill_process
from st2tests.base import IntegrationTestCase


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ST2_CONFIG_PATH = os.path.join(BASE_DIR, "../../../conf/st2.tests.conf")


class GunicornWSGIEntryPointTestCase(IntegrationTestCase):
    @pytest.mark.skipif(profiling.is_enabled(), reason="Profiling is enabled")
    def test_st2api_wsgi_entry_point(self):
        port = random.randint(10000, 30000)
        cmd = (
            'gunicorn st2api.wsgi:application -k eventlet -b "127.0.0.1:%s" --workers 1'
            % port
        )
        env = os.environ.copy()
        env["ST2_CONFIG_PATH"] = ST2_CONFIG_PATH
        env.update(st2tests.config.db_opts_as_env_vars())
        env.update(st2tests.config.mq_opts_as_env_vars())
        env.update(st2tests.config.coord_opts_as_env_vars())
        process = subprocess.Popen(cmd, env=env, shell=True, preexec_fn=os.setsid)
        try:
            self.add_process(process=process)
            eventlet.sleep(8)
            self.assertProcessIsRunning(process=process)
            response = requests.get("http://127.0.0.1:%s/v1/actions" % (port))
            self.assertEqual(response.status_code, http_client.OK)
        finally:
            kill_process(process)

    @pytest.mark.skipif(profiling.is_enabled(), reason="Profiling is enabled")
    def test_st2auth(self):
        port = random.randint(10000, 30000)
        cmd = (
            'gunicorn st2auth.wsgi:application -k eventlet -b "127.0.0.1:%s" --workers 1'
            % port
        )
        env = os.environ.copy()
        env["ST2_CONFIG_PATH"] = ST2_CONFIG_PATH
        env.update(st2tests.config.db_opts_as_env_vars())
        env.update(st2tests.config.mq_opts_as_env_vars())
        env.update(st2tests.config.coord_opts_as_env_vars())
        process = subprocess.Popen(cmd, env=env, shell=True, preexec_fn=os.setsid)
        try:
            self.add_process(process=process)
            eventlet.sleep(8)
            self.assertProcessIsRunning(process=process)
            response = requests.post("http://127.0.0.1:%s/tokens" % (port))
            self.assertEqual(response.status_code, http_client.UNAUTHORIZED)
        finally:
            kill_process(process)
