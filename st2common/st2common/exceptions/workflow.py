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

from st2common import exceptions as st2_exc
from st2common.exceptions import db as db_exc
from st2common import log as logging


LOG = logging.getLogger(__name__)


def retry_on_exceptions(exc):
    LOG.warning('Determining if exception %s should be retried.', type(exc))

    retrying = isinstance(exc, db_exc.StackStormDBObjectWriteConflictError)

    if retrying:
        LOG.warning('Retrying operation due to database write conflict.')

    return retrying


class WorkflowDefinitionException(st2_exc.StackStormBaseException):
    pass


class WorkflowExecutionNotFoundException(st2_exc.StackStormBaseException):

    def __init__(self, ac_ex_id):
        Exception.__init__(
            self,
            'Unable to identify any workflow execution that is '
            'associated to action execution "%s".' % ac_ex_id
        )


class AmbiguousWorkflowExecutionException(st2_exc.StackStormBaseException):

    def __init__(self, ac_ex_id):
        Exception.__init__(
            self,
            'More than one workflow execution is associated '
            'to action execution "%s".' % ac_ex_id
        )


class WorkflowExecutionIsCompletedException(st2_exc.StackStormBaseException):

    def __init__(self, wf_ex_id):
        Exception.__init__(self, 'Workflow execution "%s" is already completed.' % wf_ex_id)


class WorkflowExecutionIsRunningException(st2_exc.StackStormBaseException):

    def __init__(self, wf_ex_id):
        Exception.__init__(self, 'Workflow execution "%s" is already active.' % wf_ex_id)
