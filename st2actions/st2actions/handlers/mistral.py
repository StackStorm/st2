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

import ast
import eventlet
import json
import re
import requests

from oslo_config import cfg
from mistralclient.api import client as mistral
from mistralclient.api.v2 import action_executions

from st2common.constants import action as action_constants
from st2common import log as logging
from st2actions import handlers


LOG = logging.getLogger(__name__)


STATUS_MAP = dict()
STATUS_MAP[action_constants.LIVEACTION_STATUS_REQUESTED] = 'RUNNING'
STATUS_MAP[action_constants.LIVEACTION_STATUS_SCHEDULED] = 'RUNNING'
STATUS_MAP[action_constants.LIVEACTION_STATUS_RUNNING] = 'RUNNING'
STATUS_MAP[action_constants.LIVEACTION_STATUS_SUCCEEDED] = 'SUCCESS'
STATUS_MAP[action_constants.LIVEACTION_STATUS_FAILED] = 'ERROR'


def get_handler():
    return MistralCallbackHandler


def get_action_execution_id_from_url(url):
    match = re.search('(.+)/action_executions/(.+)', url)
    if not match or len(match.groups()) != 2:
        raise ValueError('Unable to extract the action execution ID '
                         'from the callback URL (%s).' % url)

    return match.group(2)


class MistralCallbackHandler(handlers.ActionExecutionCallbackHandler):

    @staticmethod
    def callback(url, context, status, result):
        if status not in [action_constants.LIVEACTION_STATUS_SUCCEEDED,
                          action_constants.LIVEACTION_STATUS_FAILED]:
            return

        try:
            if isinstance(result, basestring) and len(result) > 0 and result[0] in ['{', '[']:
                value = ast.literal_eval(result)
                if type(value) in [dict, list]:
                    result = value

            action_execution_id = get_action_execution_id_from_url(url)
            output = json.dumps(result) if type(result) in [dict, list] else str(result)
            data = {'state': STATUS_MAP[status], 'output': output}

            client = mistral.client(
                mistral_url=cfg.CONF.mistral.v2_base_url,
                username=cfg.CONF.mistral.keystone_username,
                api_key=cfg.CONF.mistral.keystone_password,
                project_name=cfg.CONF.mistral.keystone_project_name,
                auth_url=cfg.CONF.mistral.keystone_auth_url)

            manager = action_executions.ActionExecutionManager(client)

            for i in range(cfg.CONF.mistral.max_attempts):
                try:
                    LOG.info('Sending callback to %s with data %s.', url, data)
                    manager.update(action_execution_id, **data)
                    break
                except requests.exceptions.ConnectionError as conn_exc:
                    LOG.exception(conn_exc)
                    if i < cfg.CONF.mistral.max_attempts:
                        eventlet.sleep(cfg.CONF.mistral.retry_wait)
        except Exception as e:
            LOG.exception(e)
