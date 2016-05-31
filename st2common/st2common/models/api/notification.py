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
        "routes": {
            "type": "array",
            "description": "Channels to post notifications to."
        },
        "channels": {  # Deprecated. Only here for backward compatibility.
            "type": "array",
            "description": "Channels to post notifications to."
        },
    },
    "additionalProperties": False
}


class NotificationsHelper(object):

    @staticmethod
    def to_model(notify_api_object):
        if notify_api_object.get('on-success', None):
            on_success = NotificationsHelper._to_model_sub_schema(notify_api_object['on-success'])
        else:
            on_success = None

        if notify_api_object.get('on-complete', None):
            on_complete = NotificationsHelper._to_model_sub_schema(
                notify_api_object['on-complete'])
        else:
            on_complete = None

        if notify_api_object.get('on-failure', None):
            on_failure = NotificationsHelper._to_model_sub_schema(notify_api_object['on-failure'])
        else:
            on_failure = None

        model = NotificationSchema(on_success=on_success, on_failure=on_failure,
                                   on_complete=on_complete)
        return model

    @staticmethod
    def _to_model_sub_schema(notification_settings_json):
        message = notification_settings_json.get('message', None)
        data = notification_settings_json.get('data', {})
        routes = (notification_settings_json.get('routes', None) or
                  notification_settings_json.get('channels', []))

        model = NotificationSubSchema(message=message, data=data, routes=routes)
        return model

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
        if getattr(notify_sub_schema_model, 'data', None):
            notify_sub_schema['data'] = notify_sub_schema_model.data
        routes = (getattr(notify_sub_schema_model, 'routes') or
                  getattr(notify_sub_schema_model, 'channels'))
        if routes:
            notify_sub_schema['routes'] = routes

        return notify_sub_schema
