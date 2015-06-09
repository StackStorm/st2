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

from st2common.models.db.notification import NotificationSchema, NotificationSubSchema

NotificationSubSchemaAPI = {
    "type": "object",
    "properties": {
        "message": {
            "type": "string",
            "description": "Message to use for notification"
        },
        "data": {
            "type": "object",
            "description": "Data to be sent as part of notification"
        },
        "channels": {
            "type": "array",
            "description": "Channels to post notifications to."
        },
    },
    "additionalProperties": False
}


class NotificationsHelper(object):

    @staticmethod
    def to_model(notify_api_object):
        model = NotificationSchema()
        if notify_api_object.get('on-complete', None):
            model.on_complete = NotificationsHelper._to_model_sub_schema(
                notify_api_object['on-complete'])
        if notify_api_object.get('on-success', None):
            model.on_success = NotificationsHelper._to_model_sub_schema(
                notify_api_object['on-success'])
        if notify_api_object.get('on-failure', None):
            model.on_failure = NotificationsHelper._to_model_sub_schema(
                notify_api_object['on-failure'])
        return model

    @staticmethod
    def _to_model_sub_schema(notification_settings_json):
        notify_sub_schema = NotificationSubSchema()
        notify_sub_schema.message = notification_settings_json.get('message' or None)
        notify_sub_schema.data = notification_settings_json.get('data' or {})
        notify_sub_schema.channels = notification_settings_json.get('channels' or [])
        return notify_sub_schema

    @staticmethod
    def from_model(notify_model):
        notify = {}
        if getattr(notify_model, 'on_complete', None):
            notify['on-complete'] = NotificationsHelper._from_model_sub_schema(
                notify_model.on_complete)
        if getattr(notify_model, 'on_success', None):
            notify['on-success'] = NotificationsHelper._from_model_sub_schema(
                notify_model.on_success)
        if getattr(notify_model, 'on_failure', None):
            notify['on-failure'] = NotificationsHelper._from_model_sub_schema(
                notify_model.on_failure)
        return notify

    @staticmethod
    def _from_model_sub_schema(notify_sub_schema_model):
        notify_sub_schema = {}

        if getattr(notify_sub_schema_model, 'message', None):
            notify_sub_schema['message'] = notify_sub_schema_model.message
        if getattr(notify_sub_schema_model, 'message', None):
            notify_sub_schema['data'] = notify_sub_schema_model.data
        if getattr(notify_sub_schema_model, 'channels', None):
            notify_sub_schema['channels'] = notify_sub_schema_model.channels

        return notify_sub_schema
