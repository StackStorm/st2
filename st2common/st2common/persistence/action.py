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

from oslo.config import cfg
from st2common.persistence import Access
from st2common.models.db.action import (runnertype_access, action_access, actionexec_access)
from st2common.models.db.action import actionexecstate_access
from st2common import transport


class RunnerType(Access):
    impl = runnertype_access

    @classmethod
    def _get_impl(kls):
        return kls.impl


class Action(Access):
    impl = action_access

    @classmethod
    def _get_impl(kls):
        return kls.impl


class ActionExecution(Access):
    impl = actionexec_access
    publisher = None

    @classmethod
    def _get_impl(kls):
        return kls.impl

    @classmethod
    def _get_publisher(kls):
        if not kls.publisher:
            kls.publisher = transport.actionexecution.ActionExecutionPublisher(
                cfg.CONF.messaging.url)
        return kls.publisher


class ActionExecutionState(Access):
    impl = actionexecstate_access

    @classmethod
    def _get_impl(kls):
        return kls.impl
