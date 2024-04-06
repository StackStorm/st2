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

"""
This tests whether an action which is python-script behaves as we expect.
"""

import os
import mock
import tempfile

from st2common.util.monkey_patch import use_select_poll_workaround

use_select_poll_workaround()

from oslo_config import cfg

from python_runner import python_runner
from st2common.util.virtualenvs import setup_pack_virtualenv
from st2tests import config
from st2tests.base import CleanFilesTestCase
from st2tests.base import CleanDbTestCase
from st2tests.fixtures.packs.test_library_dependencies.fixture import (
    PACK_NAME as TEST_LIBRARY_DEPENDENCIES,
)
from st2tests.fixturesloader import get_fixtures_base_path

__all__ = ["PythonRunnerBehaviorTestCase"]

FIXTURES_BASE_PATH = get_fixtures_base_path()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WRAPPER_SCRIPT_PATH = os.path.join(
    BASE_DIR, "../../../python_runner/python_runner/python_action_wrapper.py"
)
WRAPPER_SCRIPT_PATH = os.path.abspath(WRAPPER_SCRIPT_PATH)


class PythonRunnerBehaviorTestCase(CleanFilesTestCase, CleanDbTestCase):

    # If you need these logs, then you probably also want to uncomment
    # extra debug log messages in st2common/st2common/util/virtualenvs.py
    # and pass --logging-level=DEBUG to nosetests
    # DISPLAY_LOG_MESSAGES = True

    def setUp(self):
        super(PythonRunnerBehaviorTestCase, self).setUp()
        config.parse_args()

        dir_path = tempfile.mkdtemp()
        cfg.CONF.set_override(name="base_path", override=dir_path, group="system")

        self.base_path = dir_path
        self.virtualenvs_path = os.path.join(self.base_path, "virtualenvs/")

        # Make sure dir is deleted on tearDown
        self.to_delete_directories.append(self.base_path)

    def test_priority_of_loading_library_after_setup_pack_virtualenv(self):
        """
        This test checks priority of loading library, whether the library which is specified in
        the 'requirements.txt' of pack is loaded when a same name module is also specified in the
        'requirements.txt' of st2, at a subprocess in ActionRunner.

        To test above, this uses 'get_library_path.py' action in 'test_library_dependencies' pack.
        This action returns file-path of imported module which is specified by 'module' parameter.
        """
        pack_name = TEST_LIBRARY_DEPENDENCIES

        # Before calling action, this sets up virtualenv for test pack. This pack has
        # requirements.txt wihch only writes 'six' module.
        setup_pack_virtualenv(pack_name=pack_name)
        self.assertTrue(os.path.exists(os.path.join(self.virtualenvs_path, pack_name)))

        # This test suite expects that loaded six module is located under the virtualenv library,
        # because 'six' is written in the requirements.txt of 'test_library_dependencies' pack.
        (_, output, _) = self._run_action(
            pack_name, "get_library_path.py", {"module": "six"}
        )
        # FIXME: This test fails if system site-packages has six because
        # it won't get installed in the virtualenv (w/ --system-site-packages)
        # system site-packages is never from a virtualenv.
        # Travis has python installed in /opt/python/3.6.7
        # with a no-system-site-packages virtualenv at /home/travis/virtualenv/python3.6.7
        # GitHub Actions python is in /opt/hostedtoolcache/Python/3.6.13/x64/
        # But ther isn't a virtualenv, so when we pip installed `virtualenv`,
        # (which depends on, and therefore installs `six`)
        # we installed it in system-site-packages not an intermediate virtualenv
        self.assertEqual(output["result"].find(self.virtualenvs_path), 0)

        # Conversely, this expects that 'mock' module file-path is not under sandbox library,
        # but the parent process's library path, because that is not under the pack's virtualenv.
        (_, output, _) = self._run_action(
            pack_name, "get_library_path.py", {"module": "mock"}
        )
        self.assertEqual(output["result"].find(self.virtualenvs_path), -1)

        # While a module which is in the pack's virtualenv library is specified at 'module'
        # parameter of the action, this test suite expects that file-path under the parent's
        # library is returned when 'sandbox' parameter of PythonRunner is False.
        (_, output, _) = self._run_action(
            pack_name, "get_library_path.py", {"module": "six"}, {"_sandbox": False}
        )
        self.assertEqual(output["result"].find(self.virtualenvs_path), -1)

    def _run_action(self, pack, action, params, runner_params={}):
        action_db = mock.Mock()
        action_db.pack = pack

        runner = python_runner.get_runner()
        runner.runner_parameters = {}
        runner.action = action_db
        runner._use_parent_args = False

        for key, value in runner_params.items():
            setattr(runner, key, value)

        runner.entry_point = os.path.join(
            FIXTURES_BASE_PATH, f"packs/{pack}/actions/{action}"
        )
        runner.pre_run()
        return runner.run(params)
