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

import unittest2

from st2common.models.db.pack import PackDB
from st2common.util.pack import get_pack_common_libs_path


class PackUtilsTestCase(unittest2.TestCase):

    def test_get_pack_common_libs_path(self):
        pack_model_args = {
            'name': 'Yolo CI',
            'ref': 'yolo_ci',
            'description': 'YOLO CI pack',
            'version': '0.1.0',
            'author': 'Volkswagen',
            'path': '/opt/stackstorm/packs/yolo_ci/'
        }
        pack_db = PackDB(**pack_model_args)
        lib_path = get_pack_common_libs_path(pack_db)
        self.assertEqual('/opt/stackstorm/packs/yolo_ci/lib', lib_path)

    def test_get_pack_common_libs_path_no_path_in_pack_db(self):
        pack_model_args = {
            'name': 'Yolo CI',
            'ref': 'yolo_ci',
            'description': 'YOLO CI pack',
            'version': '0.1.0',
            'author': 'Volkswagen'
        }
        pack_db = PackDB(**pack_model_args)
        lib_path = get_pack_common_libs_path(pack_db)
        self.assertEqual(None, lib_path)
