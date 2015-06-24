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
import requests

from oslo_config import cfg

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


class MistralCallbackHandler(handlers.ActionExecutionCallbackHandler):

    @staticmethod
    def callback(url, context, status, result):
        if status not in [action_constants.LIVEACTION_STATUS_SUCCEEDED,
                          action_constants.LIVEACTION_STATUS_FAILED]:
            return

        try:
            method = 'PUT'
            headers = {'content-type': 'application/json'}

            if isinstance(result, basestring) and len(result) > 0 and result[0] in ['{', '[']:
                value = ast.literal_eval(result)
                if type(value) in [dict, list]:
                    result = value

            if isinstance(result, dict):
                # Remove the list of tasks created by the results
                # tracker before sending the output.
                result.pop('tasks', None)

            output = json.dumps(result) if type(result) in [dict, list] else str(result)
            data = {'state': STATUS_MAP[status], 'output': output}

            for i in range(cfg.CONF.mistral.max_attempts):
                try:
                    LOG.info('Sending callback to %s with data %s.', url, data)
                    response = requests.request(method, url, data=json.dumps(data), headers=headers)
                    if response.status_code == 200:
                        break
                except requests.exceptions.ConnectionError as conn_exc:
                    LOG.exception(conn_exc)
                    if i < cfg.CONF.mistral.max_attempts:
                        eventlet.sleep(cfg.CONF.mistral.retry_wait)

            if response and response.status_code != 200:
                response.raise_for_status()

        except Exception as e:
            LOG.exception(e)
