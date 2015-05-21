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

import jsonschema
import pecan
import six

from mongoengine import ValidationError
from pecan import rest
from st2common import log as logging
from st2common.models.api.base import jsexpose
from st2common.models.api.action import AliasExecutionAPI
from st2common.models.db.action import LiveActionDB, NotificationSchema, NotificationSubSchema
from st2common.models.utils import action_alias_utils, action_param_utils
from st2common.persistence.action import ActionAlias
from st2common.services import action as action_service
from st2common.exceptions.db import StackStormDBObjectNotFoundError


http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class ActionAliasExecutionController(rest.RestController):

    @jsexpose(body_cls=AliasExecutionAPI, status_code=http_client.OK)
    def post(self, payload):
        action_alias_name = payload.name if payload else None

        if not action_alias_name:
            pecan.abort(http_client.BAD_REQUEST, 'Alias execution "name" is required')

        format = payload.format or ''
        command = payload.command or ''

        try:
            action_alias_db = ActionAlias.get_by_name(action_alias_name)
        except ValueError:
            action_alias_db = None

        if not action_alias_db:
            msg = 'Unable to identify action alias with name "%s".' % action_alias_name
            pecan.abort(http_client.NOT_FOUND, msg)

        execution_parameters = self._extract_parameters(action_alias_db=action_alias_db,
                                                        format=format,
                                                        param_stream=command)
        notify = self._get_notify_field(payload)
        execution = self._schedule_execution(action_alias_db=action_alias_db,
                                             params=execution_parameters,
                                             notify=notify)

        return str(execution.id)

    def _tokenize_alias_execution(self, alias_execution):
        tokens = alias_execution.strip().split(' ', 1)
        return (tokens[0], tokens[1] if len(tokens) > 1 else None)

    def _extract_parameters(self, action_alias_db, format, param_stream):
        if action_alias_db.formats and format in action_alias_db.formats:
            alias_format = format
        else:
            alias_format = None

        parser = action_alias_utils.ActionAliasFormatParser(alias_format=alias_format,
                                                            param_stream=param_stream)
        return parser.get_extracted_param_value()

    def _get_notify_field(self, payload):
        on_complete = NotificationSubSchema()
        on_complete.channels = [payload.notification_channel]
        on_complete.data = {
            'user': payload.user,
            'source_channel': payload.source_channel
        }
        notify = NotificationSchema()
        notify.on_complete = on_complete
        return notify

    def _schedule_execution(self, action_alias_db, params, notify):
        try:
            # prior to shipping off the params cast them to the right type.
            params = action_param_utils.cast_params(action_ref=action_alias_db.action_ref,
                                                    params=params)
            liveaction = LiveActionDB(action=action_alias_db.action_ref, context={},
                                      parameters=params, notify=notify)
            _, action_execution_db = action_service.request(liveaction)
            return action_execution_db
        except ValueError as e:
            LOG.exception('Unable to execute action.')
            pecan.abort(http_client.BAD_REQUEST, str(e))
        except jsonschema.ValidationError as e:
            LOG.exception('Unable to execute action. Parameter validation failed.')
            pecan.abort(http_client.BAD_REQUEST, str(e))
        except Exception as e:
            LOG.exception('Unable to execute action. Unexpected error encountered.')
            pecan.abort(http_client.INTERNAL_SERVER_ERROR, str(e))
