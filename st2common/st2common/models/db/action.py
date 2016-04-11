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

import mongoengine as me

from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.models.db.actionalias import ActionAliasDB
from st2common.models.db.executionstate import ActionExecutionStateDB
from st2common.models.db.execution import ActionExecutionDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.notification import NotificationSchema
from st2common.models.db.runner import RunnerTypeDB
from st2common.constants.action import WORKFLOW_RUNNER_TYPES
from st2common.constants.types import ResourceType

__all__ = [
    'RunnerTypeDB',
    'ActionDB',
    'LiveActionDB',
    'ActionExecutionDB',
    'ActionExecutionStateDB',
    'ActionAliasDB'
]


LOG = logging.getLogger(__name__)

PACK_SEPARATOR = '.'


class ActionDB(stormbase.StormFoundationDB, stormbase.TagsMixin,
               stormbase.ContentPackResourceMixin, stormbase.UIDFieldMixin):
    """
    The system entity that represents a Stack Action/Automation in the system.

    Attribute:
        enabled: A flag indicating whether this action is enabled in the system.
        entry_point: The entry point to the action.
        runner_type: The actionrunner is used to execute the action.
        parameters: The specification for parameters for the action.
    """

    RESOURCE_TYPE = ResourceType.ACTION
    UID_FIELDS = ['pack', 'name']

    name = me.StringField(required=True)
    ref = me.StringField(required=True)
    description = me.StringField()
    enabled = me.BooleanField(
        required=True, default=True,
        help_text='A flag indicating whether the action is enabled.')
    entry_point = me.StringField(
        required=True,
        help_text='The entry point to the action.')
    pack = me.StringField(
        required=False,
        help_text='Name of the content pack.',
        unique_with='name')
    runner_type = me.DictField(
        required=True, default={},
        help_text='The action runner to use for executing the action.')
    parameters = stormbase.EscapedDynamicField(
        help_text='The specification for parameters for the action.')
    notify = me.EmbeddedDocumentField(NotificationSchema)

    meta = {
        'indexes': stormbase.TagsMixin.get_indices() + stormbase.UIDFieldMixin.get_indexes()
    }

    def __init__(self, *args, **values):
        super(ActionDB, self).__init__(*args, **values)
        self.ref = self.get_reference().ref
        self.uid = self.get_uid()

    def is_workflow(self):
        """
        Return True if this action is a workflow, False otherwise.

        :rtype: ``bool``
        """
        # pylint: disable=unsubscriptable-object
        return self.runner_type['name'] in WORKFLOW_RUNNER_TYPES

# specialized access objects
action_access = MongoDBAccess(ActionDB)

MODELS = [ActionDB, ActionExecutionDB, ActionExecutionStateDB, ActionAliasDB,
          LiveActionDB, RunnerTypeDB]
