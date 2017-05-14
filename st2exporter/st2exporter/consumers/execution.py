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

from st2common import log as logging

from st2common.constants.action import (LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED,
                                        LIVEACTION_STATUS_CANCELED)
from st2exporter.consumers.base import ModelExporter
from st2common.models.api.execution import ActionExecutionAPI
from st2common.models.db.execution import ActionExecutionDB
from st2common.persistence.execution import ActionExecution

__all__ = [
    'ExecutionsExporter'
]

COMPLETION_STATUSES = [LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED,
                       LIVEACTION_STATUS_CANCELED]
LOG = logging.getLogger(__name__)


class ExecutionsExporter(ModelExporter):
    message_type = ActionExecutionDB
    api_model = ActionExecutionAPI
    persistence_model = ActionExecution

    def __init__(self, connection, queues):
        super(ExecutionsExporter, self).__init__(
            model_type='executions',
            connection=connection,
            queues=queues)

    def should_export(self, model):
        return model.status in COMPLETION_STATUSES
