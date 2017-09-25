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

import Queue
import time

from unittest2 import TestCase
import mock


from st2common.query.base import Querier
from st2tests.config import parse_args
parse_args()


class QueryBaseTests(TestCase):

    @mock.patch.object(
        Querier,
        '_query_and_save_results',
        mock.MagicMock(return_value=True)
    )
    def test_fire_queries_doesnt_loop(self):
        querier = Querier()

        mock_query_state_1 = {
            'execution_id': '59194ff9adf592042d3005bf',
            'query_module': 'mistral_v2',
            'query_context': {
                'mistral': {
                    'workflow_name': 'st2ci.st2_pkg_e2e_test',
                    'execution_id': '6d624534-42ca-425c-aa3a-ccc676386fb2'
                }
            }
        }

        mock_query_state_2 = {
            'execution_id': '59194ff9adf592042d3005bg',
            'query_module': 'mistral_v2',
            'query_context': {
                'mistral': {
                    'workflow_name': 'st2ci.st2_pkg_e2e_test',
                    'execution_id': '6d624534-42ca-425c-aa3a-ccc676386fb3'
                }
            }
        }

        mock_query_state_3 = {
            'execution_id': '59194ff9adf592042d3005bh',
            'query_module': 'mistral_v2',
            'query_context': {
                'mistral': {
                    'workflow_name': 'st2ci.st2_pkg_e2e_test',
                    'execution_id': '6d624534-42ca-425c-aa3a-ccc676386fb4'
                }
            }
        }

        now = time.time()

        query_contexts = Queue.Queue()
        query_contexts.put((now + 100000, mock_query_state_1)),
        query_contexts.put((now + 100001, mock_query_state_2)),
        query_contexts.put((now - 200000, mock_query_state_3)),
        querier._query_contexts = query_contexts
        querier._fire_queries()
        self.assertEqual(querier._query_contexts.qsize(), 2)
