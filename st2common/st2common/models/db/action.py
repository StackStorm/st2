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

import datetime
import mongoengine as me

from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.fields import ComplexDateTimeField

__all__ = [
    'RunnerTypeDB',
    'ActionDB',
    'LiveActionDB',
    'ActionExecutionStateDB',
    'ActionAliasDB'
]


LOG = logging.getLogger(__name__)

PACK_SEPARATOR = '.'


class RunnerTypeDB(stormbase.StormBaseDB):
    """
    The representation of an RunnerType in the system. An RunnerType
    has a one-to-one mapping to a particular ActionRunner implementation.

    Attributes:
        id: See StormBaseAPI
        name: See StormBaseAPI
        description: See StormBaseAPI
        enabled: A flag indicating whether the runner for this type is enabled.
        runner_module: The python module that implements the action runner for this type.
        runner_parameters: The specification for parameters for the action runner.
    """

    enabled = me.BooleanField(
        required=True, default=True,
        help_text='A flag indicating whether the runner for this type is enabled.')
    runner_module = me.StringField(
        required=True,
        help_text='The python module that implements the action runner for this type.')
    runner_parameters = me.DictField(
        help_text='The specification for parameters for the action runner.')
    query_module = me.StringField(
        required=False,
        help_text='The python module that implements the query module for this runner.')


class NotificationSubSchema(me.EmbeddedDocument):
    """
        Schema for notification settings to be specified for action success/failure.
    """
    message = me.StringField()
    data = stormbase.EscapedDynamicField(
        default={},
        help_text='Payload to be sent as part of notification.')
    channels = me.ListField(
        default=['notify.default'],
        help_text='Channels to post notifications to.')

    def __str__(self):
        result = []
        result.append('NotificationSubSchema@')
        result.append(str(id(self)))
        result.append('(message="%s", ' % str(self.message))
        result.append('data="%s", ' % str(self.data))
        result.append('channels="%s")' % str(self.channels))
        return ''.join(result)


class NotificationSchema(me.EmbeddedDocument):
    """
        Schema for notification settings to be specified for actions.
    """
    on_success = me.EmbeddedDocumentField(NotificationSubSchema)
    on_failure = me.EmbeddedDocumentField(NotificationSubSchema)
    on_complete = me.EmbeddedDocumentField(NotificationSubSchema)

    def __str__(self):
        result = []
        result.append('NotifySchema@')
        result.append(str(id(self)))
        result.append('(on_complete="%s", ' % str(self.on_complete))
        result.append('on_success="%s", ' % str(self.on_success))
        result.append('on_failure="%s")' % str(self.on_failure))
        return ''.join(result)


class ActionDB(stormbase.StormContentDB, stormbase.TagsMixin,
               stormbase.ContentPackResourceMixin):
    """
    The system entity that represents a Stack Action/Automation in the system.

    Attribute:
        enabled: A flag indicating whether this action is enabled in the system.
        entry_point: The entry point to the action.
        runner_type: The actionrunner is used to execute the action.
        parameters: The specification for parameters for the action.
    """
    ref = me.StringField(required=True)
    enabled = me.BooleanField(
        required=True, default=True,
        help_text='A flag indicating whether the action is enabled.')
    entry_point = me.StringField(
        required=True,
        help_text='The entry point to the action.')
    runner_type = me.DictField(
        required=True, default={},
        help_text='The action runner to use for executing the action.')
    parameters = me.DictField(
        help_text='The specification for parameters for the action.')
    notify = me.EmbeddedDocumentField(NotificationSchema)

    meta = {
        'indexes': stormbase.TagsMixin.get_indices()
    }


class LiveActionDB(stormbase.StormFoundationDB):
    """
        The databse entity that represents a Stack Action/Automation in
        the system.

        Attributes:
            status: the most recently observed status of the execution.
                    One of "starting", "running", "completed", "error".
            result: an embedded document structure that holds the
                    output and exit status code from the action.
    """

    # TODO: Can status be an enum at the Mongo layer?
    status = me.StringField(
        required=True,
        help_text='The current status of the liveaction.')
    start_timestamp = ComplexDateTimeField(
        default=datetime.datetime.utcnow,
        help_text='The timestamp when the liveaction was created.')
    end_timestamp = ComplexDateTimeField(
        help_text='The timestamp when the liveaction has finished.')
    action = me.StringField(
        required=True,
        help_text='Reference to the action that has to be executed.')
    parameters = me.DictField(
        default={},
        help_text='The key-value pairs passed as to the action runner &  execution.')
    result = stormbase.EscapedDynamicField(
        default={},
        help_text='Action defined result.')
    context = me.DictField(
        default={},
        help_text='Contextual information on the action execution.')
    callback = me.DictField(
        default={},
        help_text='Callback information for the on completion of action execution.')
    runner_info = me.DictField(
        default={},
        help_text='Reference to the runner that executed this liveaction.')
    notify = me.EmbeddedDocumentField(NotificationSchema)

    meta = {
        'indexes': ['-start_timestamp', 'action']
    }


class ActionExecutionStateDB(stormbase.StormFoundationDB):
    """
        Database entity that represents the state of Action execution.
    """

    execution_id = me.ObjectIdField(
        required=True,
        unique=True,
        help_text='liveaction ID.')
    query_module = me.StringField(
        required=True,
        help_text='Reference to the runner model.')
    query_context = me.DictField(
        required=True,
        help_text='Context about the action execution that is needed for results query.')

    meta = {
        'indexes': ['query_module']
    }


class ActionAliasDB(stormbase.StormBaseDB):
    """
        Database entity that represent an Alias for an action.
    """
    action_ref = me.StringField(
        required=True,
        help_text='Reference of the Action map this alias.')
    formats = me.ListField(
        field=me.StringField(),
        help_text='Possible parameter formats that an alias supports.')
    file_uri = me.StringField(
        required=False,
        help_text='Location of the content metadata file.')

    meta = {
        'indexes': ['name']
    }


# specialized access objects
runnertype_access = MongoDBAccess(RunnerTypeDB)
action_access = MongoDBAccess(ActionDB)
liveaction_access = MongoDBAccess(LiveActionDB)
actionexecstate_access = MongoDBAccess(ActionExecutionStateDB)
actionalias_access = MongoDBAccess(ActionAliasDB)


MODELS = [RunnerTypeDB, ActionDB, LiveActionDB, ActionExecutionStateDB, ActionAliasDB]
