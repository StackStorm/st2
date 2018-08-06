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

from __future__ import absolute_import

from st2common.util import loader


def get_wf_fixture_meta_data(fixture_pack_path, wf_meta_file_name):
    wf_meta_file_path = fixture_pack_path + '/actions/' + wf_meta_file_name
    wf_meta_content = loader.load_meta_file(wf_meta_file_path)
    wf_name = wf_meta_content['pack'] + '.' + wf_meta_content['name']

    return {
        'file_name': wf_meta_file_name,
        'file_path': wf_meta_file_path,
        'content': wf_meta_content,
        'name': wf_name
    }
