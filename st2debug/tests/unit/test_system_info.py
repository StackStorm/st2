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

import mock
import unittest2

import st2debug.utils.system_info
from st2debug.utils.system_info import get_cpu_info
from st2debug.utils.system_info import get_memory_info
from st2debug.utils.system_info import get_deb_package_list
from st2debug.utils.system_info import get_rpm_package_list

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(BASE_DIR, '../fixtures')

orig_cpu_info = st2debug.utils.system_info.CPU_INFO_PATH
orig_mem_info = st2debug.utils.system_info.MEMORY_INFO_PATH


class SystemInfoTestCase(unittest2.TestCase):
    def setUp(self):
        st2debug.utils.system_info.CPU_INFO_PATH = orig_cpu_info
        st2debug.utils.system_info.MEMORY_INFO_PATH = orig_mem_info

    def test_get_cpu_info_success(self):
        st2debug.utils.system_info.CPU_INFO_PATH = os.path.join(FIXTURES_DIR,
                                                                'proc_cpuinfo')

        cpu_info = get_cpu_info()
        self.assertEqual(len(cpu_info), 4)
        self.assertEqual(cpu_info[0]['model_name'], 'Intel(R) Core(TM) i7-2640M CPU @ 2.80GHz')

    def test_get_cpu_info_no_procinfo_file(self):
        st2debug.utils.system_info.CPU_INFO_PATH = 'doesntexist'

        cpu_info = get_cpu_info()
        self.assertEqual(cpu_info, {})

    def test_get_memory_info_success(self):
        st2debug.utils.system_info.MEMORY_INFO_PATH = os.path.join(FIXTURES_DIR,
                                                                   'proc_meminfo')

        memory_info = get_memory_info()
        self.assertEqual(memory_info['MemTotal'], 16313772)
        self.assertEqual(memory_info['MemFree'], 8445896)
        self.assertEqual(memory_info['MemAvailable'], 10560460)

    def test_get_memory_info_no_meminfo_file(self):
        st2debug.utils.system_info.MEMORY_INFO_PATH = 'doesntexist'

        memory_info = get_memory_info()
        self.assertEqual(memory_info, {})

    @mock.patch('st2debug.utils.system_info.run_command')
    def test_get_deb_package_list(self, mock_run_command):
        file_path = os.path.join(FIXTURES_DIR, 'deb_pkg_list')
        with open(file_path, 'r') as fp:
            mock_stdout = fp.read()

        mock_run_command.return_value = (0, mock_stdout, '')

        package_list = get_deb_package_list(name_startswith='st2')
        self.assertEqual(len(package_list), 5)
        self.assertEqual(package_list[0]['name'], 'st2actions')
        self.assertEqual(package_list[0]['version'], '0.6.0-11')

    @mock.patch('st2debug.utils.system_info.run_command')
    def test_get_rpm_package_list(self, mock_run_command):
        file_path = os.path.join(FIXTURES_DIR, 'rpm_pkg_list')
        with open(file_path, 'r') as fp:
            mock_stdout = fp.read()

        mock_run_command.return_value = (0, mock_stdout, '')

        package_list = get_rpm_package_list(name_startswith='st2')
        self.assertEqual(len(package_list), 6)
        self.assertEqual(package_list[0]['name'], 'st2actions')
        self.assertEqual(package_list[0]['version'], '0.7-8')
