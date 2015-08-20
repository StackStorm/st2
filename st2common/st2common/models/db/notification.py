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

from st2common.models.db import stormbase


class NotificationSubSchema(me.EmbeddedDocument):
    """
        Schema for notification settings to be specified for action success/failure.
    """
    message = me.StringField()
    data = stormbase.EscapedDynamicField(
        default={},
        help_text='Payload to be sent as part of notification.')
    routes = me.ListField(
        default=['notify.default'],
        help_text='Routes to post notifications to.')
    channels = me.ListField(  # Deprecated. Only here for backward compatibility reasons.
        default=['notify.default'],
        help_text='Routes to post notifications to.')

    def __str__(self):
        result = []
        result.append('NotificationSubSchema@')
        result.append(str(id(self)))
        result.append('(message="%s", ' % str(self.message))
        result.append('data="%s", ' % str(self.data))
        result.append('routes="%s")' % str(self.channels))
        result.append('(**deprecated**) channels="%s")' % str(self.channels))
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
