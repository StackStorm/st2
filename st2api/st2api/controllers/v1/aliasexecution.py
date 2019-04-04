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

import six
import jsonschema
from jinja2.exceptions import UndefinedError
from oslo_config import cfg

from st2api.controllers.base import BaseRestControllerMixin
from st2common import log as logging
from st2common.exceptions.actionalias import ActionAliasAmbiguityException
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.action import ActionAliasAPI
from st2common.models.api.action import AliasMatchAndExecuteInputAPI
from st2common.models.api.auth import get_system_username
from st2common.models.api.execution import ActionExecutionAPI
from st2common.models.db.auth import UserDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.notification import NotificationSchema, NotificationSubSchema
from st2common.models.utils import action_param_utils
from st2common.models.utils.action_alias_utils import extract_parameters_for_action_alias_db
from st2common.persistence.actionalias import ActionAlias
from st2common.services import action as action_service
from st2common.util import action_db as action_utils
from st2common.util import reference
from st2common.util.actionalias_matching import get_matching_alias
from st2common.util.jinja import render_values as render
from st2common.rbac.types import PermissionType
from st2common.rbac.backends import get_rbac_backend
from st2common.router import abort
from st2common.router import Response

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)

CAST_OVERRIDES = {
    'array': (lambda cs_x: [v.strip() for v in cs_x.split(',')])
}


class ActionAliasExecutionController(BaseRestControllerMixin):
    def match_and_execute(self, input_api, requester_user, show_secrets=False):
        """
            Try to find a matching alias and if one is found, schedule a new
            execution by parsing parameters from the provided command against
            the matched alias.

            Handles requests:
                POST /aliasexecution/match_and_execute
        """
        command = input_api.command

        try:
            format_ = get_matching_alias(command=command)
        except ActionAliasAmbiguityException as e:
            LOG.exception('Command "%s" matched (%s) patterns.', e.command, len(e.matches))
            return abort(http_client.BAD_REQUEST, six.text_type(e))

        action_alias_db = format_['alias']
        representation = format_['representation']

        params = {
            'name': action_alias_db.name,
            'format': representation,
            'command': command,
            'user': input_api.user,
            'source_channel': input_api.source_channel
        }

        # Add in any additional parameters provided by the user
        if input_api.notification_channel:
            params['notification_channel'] = input_api.notification_channel

        if input_api.notification_route:
            params['notification_route'] = input_api.notification_route

        alias_execution_api = AliasMatchAndExecuteInputAPI(**params)
        results = self._post(
            payload=alias_execution_api,
            requester_user=requester_user,
            show_secrets=show_secrets,
            match_multiple=format_['match_multiple'])
        return Response(json={'results': results}, status=http_client.CREATED)

    def _post(self, payload, requester_user, show_secrets=False, match_multiple=False):
        action_alias_name = payload.name if payload else None

        if not action_alias_name:
            abort(http_client.BAD_REQUEST, 'Alias execution "name" is required')
            return

        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)

        format_str = payload.format or ''
        command = payload.command or ''

        try:
            action_alias_db = ActionAlias.get_by_name(action_alias_name)
        except ValueError:
            action_alias_db = None

        if not action_alias_db:
            msg = 'Unable to identify action alias with name "%s".' % (action_alias_name)
            abort(http_client.NOT_FOUND, msg)
            return

        if not action_alias_db.enabled:
            msg = 'Action alias with name "%s" is disabled.' % (action_alias_name)
            abort(http_client.BAD_REQUEST, msg)
            return

        if match_multiple:
            multiple_execution_parameters = extract_parameters_for_action_alias_db(
                action_alias_db=action_alias_db,
                format_str=format_str,
                param_stream=command,
                match_multiple=match_multiple)
        else:
            multiple_execution_parameters = [
                extract_parameters_for_action_alias_db(
                    action_alias_db=action_alias_db,
                    format_str=format_str,
                    param_stream=command,
                    match_multiple=match_multiple)
            ]

        notify = self._get_notify_field(payload)

        context = {
            'action_alias_ref': reference.get_ref_from_model(action_alias_db),
            'api_user': payload.user,
            'user': requester_user.name,
            'source_channel': payload.source_channel
        }

        results = []
        for execution_parameters in multiple_execution_parameters:
            execution = self._schedule_execution(action_alias_db=action_alias_db,
                                                 params=execution_parameters,
                                                 notify=notify,
                                                 context=context,
                                                 show_secrets=show_secrets,
                                                 requester_user=requester_user)

            result = {
                'execution': execution,
                'actionalias': ActionAliasAPI.from_model(action_alias_db)
            }

            if action_alias_db.ack:
                try:
                    if 'format' in action_alias_db.ack:
                        message = render({'alias': action_alias_db.ack['format']}, result)['alias']

                        result.update({
                            'message': message
                        })
                except UndefinedError as e:
                    result.update({
                        'message': ('Cannot render "format" in field "ack" for alias. ' +
                                    six.text_type(e))
                    })

                try:
                    if 'extra' in action_alias_db.ack:
                        result.update({
                            'extra': render(action_alias_db.ack['extra'], result)
                        })
                except UndefinedError as e:
                    result.update({
                        'extra': ('Cannot render "extra" in field "ack" for alias. ' +
                                  six.text_type(e))
                    })

            results.append(result)

        return results

    def post(self, payload, requester_user, show_secrets=False):
        results = self._post(payload, requester_user, show_secrets, match_multiple=False)
        return Response(json=results[0], status=http_client.CREATED)

    def _tokenize_alias_execution(self, alias_execution):
        tokens = alias_execution.strip().split(' ', 1)
        return (tokens[0], tokens[1] if len(tokens) > 1 else None)

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

    def _schedule_execution(self, action_alias_db, params, notify, context, requester_user,
                            show_secrets):
        action_ref = action_alias_db.action_ref
        action_db = action_utils.get_action_by_ref(action_ref)

        if not action_db:
            raise StackStormDBObjectNotFoundError('Action with ref "%s" not found ' % (action_ref))

        rbac_utils = get_rbac_backend().get_utils_class()
        permission_type = PermissionType.ACTION_EXECUTE
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=action_db,
                                                          permission_type=permission_type)

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
            mask_secrets = self._get_mask_secrets(requester_user, show_secrets=show_secrets)
            return ActionExecutionAPI.from_model(action_execution_db, mask_secrets=mask_secrets)
        except ValueError as e:
            LOG.exception('Unable to execute action.')
            abort(http_client.BAD_REQUEST, six.text_type(e))
        except jsonschema.ValidationError as e:
            LOG.exception('Unable to execute action. Parameter validation failed.')
            abort(http_client.BAD_REQUEST, six.text_type(e))
        except Exception as e:
            LOG.exception('Unable to execute action. Unexpected error encountered.')
            abort(http_client.INTERNAL_SERVER_ERROR, six.text_type(e))


action_alias_execution_controller = ActionAliasExecutionController()
