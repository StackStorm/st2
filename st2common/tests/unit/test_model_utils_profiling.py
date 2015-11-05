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

import mock

from st2tests import DbTestCase
from st2common.persistence.auth import User
from st2common.models.utils.profiling import enable_profiling
from st2common.models.utils.profiling import disable_profiling
from st2common.models.utils.profiling import log_query_and_profile_data_for_queryset


class MongoDBProfilingTestCase(DbTestCase):
    def setUp(self):
        super(MongoDBProfilingTestCase, self).setUp()
        disable_profiling()

    @mock.patch('st2common.models.utils.profiling.LOG')
    def test_logging_profiling_is_disabled(self, mock_log):
        disable_profiling()
        queryset = User.query(name__in=['test1', 'test2'], order_by=['+aa', '-bb'], limit=1)
        result = log_query_and_profile_data_for_queryset(queryset=queryset)
        self.assertEqual(queryset, result)
        call_args_list = mock_log.debug.call_args_list
        self.assertItemsEqual(call_args_list, [])

    @mock.patch('st2common.models.utils.profiling.LOG')
    def test_logging_profiling_is_enabled(self, mock_log):
        enable_profiling()
        queryset = User.query(name__in=['test1', 'test2'], order_by=['+aa', '-bb'], limit=1)
        result = log_query_and_profile_data_for_queryset(queryset=queryset)

        call_args_list = mock_log.debug.call_args_list
        call_args = call_args_list[0][0]
        call_kwargs = call_args_list[0][1]

        expected_result = ("db.user_d_b.find({'name': {'$in': ['test1', 'test2']}})"
                           ".sort({aa: 1, bb: -1}).limit(1);")
        self.assertEqual(queryset, result)
        self.assertTrue(expected_result in call_args[0])
        self.assertTrue('mongo_query' in call_kwargs['extra'])
        self.assertTrue('mongo_shell_query' in call_kwargs['extra'])

    def test_logging_profiling_is_enabled_non_queryset_object(self):
        enable_profiling()

        # Should not throw on non QuerySet object
        queryset = 1
        result = log_query_and_profile_data_for_queryset(queryset)
        self.assertEqual(result, queryset)
