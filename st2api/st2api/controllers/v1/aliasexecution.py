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
from pecan import rest
from st2common import log as logging
from st2common.models.api.base import jsexpose
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.action import AliasExecutionAPI
from st2common.models.api.action import ActionAliasAPI
from st2common.models.api.auth import get_system_username
from st2common.models.api.execution import ActionExecutionAPI
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.notification import NotificationSchema, NotificationSubSchema
from st2common.models.utils import action_alias_utils, action_param_utils
from st2common.persistence.actionalias import ActionAlias
from st2common.services import action as action_service
from st2common.util import action_db as action_utils
from st2common.util import reference
from st2common.util.api import get_requester
from st2common.util.jinja import render_values as render
from st2common.rbac.types import PermissionType
from st2common.rbac.utils import assert_request_user_has_resource_db_permission


http_client = six.moves.http_client

LOG = logging.getLogger(__name__)

CAST_OVERRIDES = {
    'array': (lambda cs_x: [v.strip() for v in cs_x.split(',')])
}


class ActionAliasExecutionController(rest.RestController):

    @jsexpose(body_cls=AliasExecutionAPI, status_code=http_client.CREATED)
    def post(self, payload):
        action_alias_name = payload.name if payload else None

        if not action_alias_name:
            pecan.abort(http_client.BAD_REQUEST, 'Alias execution "name" is required')

        format_str = payload.format or ''
        command = payload.command or ''

        try:
            action_alias_db = ActionAlias.get_by_name(action_alias_name)
        except ValueError:
            action_alias_db = None

        if not action_alias_db:
            msg = 'Unable to identify action alias with name "%s".' % (action_alias_name)
            pecan.abort(http_client.NOT_FOUND, msg)
            return

        if not action_alias_db.enabled:
            msg = 'Action alias with name "%s" is disabled.' % (action_alias_name)
            pecan.abort(http_client.BAD_REQUEST, msg)
            return

        execution_parameters = self._extract_parameters(action_alias_db=action_alias_db,
                                                        format_str=format_str,
                                                        param_stream=command)
        notify = self._get_notify_field(payload)

        context = {
            'action_alias_ref': reference.get_ref_from_model(action_alias_db),
            'api_user': payload.user,
            'user': get_requester(),
            'source_channel': payload.source_channel
        }

        execution = self._schedule_execution(action_alias_db=action_alias_db,
                                             params=execution_parameters,
                                             notify=notify,
                                             context=context)

        result = {
            'execution': execution,
            'actionalias': ActionAliasAPI.from_model(action_alias_db)
        }

        if action_alias_db.ack and 'format' in action_alias_db.ack:
            result.update({
                'message': render({'alias': action_alias_db.ack['format']}, result)['alias']
            })

        return result

    def _tokenize_alias_execution(self, alias_execution):
        tokens = alias_execution.strip().split(' ', 1)
        return (tokens[0], tokens[1] if len(tokens) > 1 else None)

    def _extract_parameters(self, action_alias_db, format_str, param_stream):
        formats = []
        for formatstring in action_alias_db.formats:
            if isinstance(formatstring, dict) and formatstring.get('representation'):
                formats.extend(formatstring['representation'])
            else:
                formats.append(formatstring)
        if formats and format_str in formats:
            alias_format = format_str
        else:
            alias_format = None

        parser = action_alias_utils.ActionAliasFormatParser(alias_format=alias_format,
                                                            param_stream=param_stream)
        return parser.get_extracted_param_value()

    def _get_notify_field(self, payload):
        on_complete = NotificationSubSchema()
        route = (getattr(payload, 'notification_route', None) or
                 getattr(payload, 'notification_channel', None))
        on_complete.routes = [route]
        on_complete.data = {
            'user': payload.user,
            'source_channel': payload.source_channel
        }
        notify = NotificationSchema()
        notify.on_complete = on_complete
        return notify

    def _schedule_execution(self, action_alias_db, params, notify, context):
        action_ref = action_alias_db.action_ref
        action_db = action_utils.get_action_by_ref(action_ref)

        if not action_db:
            raise StackStormDBObjectNotFoundError('Action with ref "%s" not found ' % (action_ref))

        assert_request_user_has_resource_db_permission(request=pecan.request, resource_db=action_db,
            permission_type=PermissionType.ACTION_EXECUTE)

        try:
            # prior to shipping off the params cast them to the right type.
            params = action_param_utils.cast_params(action_ref=action_alias_db.action_ref,
                                                    params=params,
                                                    cast_overrides=CAST_OVERRIDES)
            if not context:
                context = {
                    'action_alias_ref': reference.get_ref_from_model(action_alias_db),
                    'user': get_system_username()
                }
            liveaction = LiveActionDB(action=action_alias_db.action_ref, context=context,
                                      parameters=params, notify=notify)
            _, action_execution_db = action_service.request(liveaction)
            return ActionExecutionAPI.from_model(action_execution_db)
        except ValueError as e:
            LOG.exception('Unable to execute action.')
            pecan.abort(http_client.BAD_REQUEST, str(e))
        except jsonschema.ValidationError as e:
            LOG.exception('Unable to execute action. Parameter validation failed.')
            pecan.abort(http_client.BAD_REQUEST, str(e))
        except Exception as e:
            LOG.exception('Unable to execute action. Unexpected error encountered.')
            pecan.abort(http_client.INTERNAL_SERVER_ERROR, str(e))
