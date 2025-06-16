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

from __future__ import absolute_import

import mongoengine
import unittest

from tooz import coordination

from st2common.exceptions import db as db_exc
from st2common.exceptions import workflow as wf_exc
from st2common.models.db import workflow as wf_db_models


class WorkflowExceptionTest(unittest.TestCase):
    def test_retry_on_transient_db_errors(self):
        instance = wf_db_models.WorkflowExecutionDB()
        exc = db_exc.StackStormDBObjectWriteConflictError(instance)
        self.assertTrue(wf_exc.retry_on_transient_db_errors(exc))

    def test_do_not_retry_on_transient_db_errors(self):
        instance = wf_db_models.WorkflowExecutionDB()
        exc = db_exc.StackStormDBObjectConflictError("foobar", "1234", instance)
        self.assertFalse(wf_exc.retry_on_transient_db_errors(exc))
        self.assertFalse(wf_exc.retry_on_transient_db_errors(NotImplementedError()))
        self.assertFalse(wf_exc.retry_on_transient_db_errors(Exception()))

    def test_retry_on_connection_errors(self):
        exc = coordination.ToozConnectionError("foobar")
        self.assertTrue(wf_exc.retry_on_connection_errors(exc))

        exc = mongoengine.connection.ConnectionFailure()
        self.assertTrue(wf_exc.retry_on_connection_errors(exc))

    def test_do_not_retry_on_connection_errors(self):
        self.assertFalse(wf_exc.retry_on_connection_errors(NotImplementedError()))
        self.assertFalse(wf_exc.retry_on_connection_errors(Exception()))
