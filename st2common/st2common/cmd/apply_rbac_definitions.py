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

"""
A script which applies RBAC definitions and role assignments stored on disk.
"""

from __future__ import absolute_import
from st2common import config
from st2common.script_setup import setup as common_setup
from st2common.script_setup import teardown as common_teardown
from st2common.rbac.loader import RBACDefinitionsLoader
from st2common.rbac.syncer import RBACDefinitionsDBSyncer

__all__ = [
    'main'
]


def setup(argv):
    common_setup(config=config, setup_db=True, register_mq_exchanges=True)


def teartown():
    common_teardown()


def apply_definitions():
    loader = RBACDefinitionsLoader()
    result = loader.load()

    role_definition_apis = list(result['roles'].values())
    role_assignment_apis = list(result['role_assignments'].values())
    group_to_role_map_apis = list(result['group_to_role_maps'].values())

    syncer = RBACDefinitionsDBSyncer()
    result = syncer.sync(role_definition_apis=role_definition_apis,
                         role_assignment_apis=role_assignment_apis,
                         group_to_role_map_apis=group_to_role_map_apis)

    return result


def main(argv):
    setup(argv)
    apply_definitions()
    teartown()
