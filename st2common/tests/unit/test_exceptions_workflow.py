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

import unittest2

from st2common.exceptions import db as db_exc
from st2common.exceptions import workflow as wf_exc
from st2common.models.db import workflow as wf_db_models


class WorkflowExceptionTest(unittest2.TestCase):

    def test_retry_on_exceptions(self):
        instance = wf_db_models.WorkflowExecutionDB()
        exc = db_exc.StackStormDBObjectWriteConflictError(instance)
        self.assertTrue(wf_exc.retry_on_exceptions(exc))

    def test_do_not_retry_on_exceptions(self):
        instance = wf_db_models.WorkflowExecutionDB()
        exc = db_exc.StackStormDBObjectConflictError('foobar', '1234', instance)
        self.assertFalse(wf_exc.retry_on_exceptions(exc))
        self.assertFalse(wf_exc.retry_on_exceptions(NotImplementedError()))
        self.assertFalse(wf_exc.retry_on_exceptions(Exception()))
