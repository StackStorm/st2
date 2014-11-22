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
import json
import requests

from st2common.constants import action
from st2common import log as logging
from st2actions import handlers


LOG = logging.getLogger(__name__)


STATUS_MAP = dict()
STATUS_MAP[action.ACTIONEXEC_STATUS_SCHEDULED] = 'RUNNING'
STATUS_MAP[action.ACTIONEXEC_STATUS_RUNNING] = 'RUNNING'
STATUS_MAP[action.ACTIONEXEC_STATUS_SUCCEEDED] = 'SUCCESS'
STATUS_MAP[action.ACTIONEXEC_STATUS_FAILED] = 'ERROR'


def get_handler():
    return MistralCallbackHandler


class MistralCallbackHandler(handlers.ActionExecutionCallbackHandler):

    @staticmethod
    def callback(url, context, status, result):
        try:
            method = 'PUT'
            if isinstance(result, basestring) and len(result) > 0 and result[0] in ['{', '[']:
                value = ast.literal_eval(result)
                if type(value) in [dict, list]:
                    result = value
            output = json.dumps(result) if type(result) in [dict, list] else str(result)
            v1 = 'v1' in url
            output_key = 'output' if v1 else 'result'
            data = {'state': STATUS_MAP[status], output_key: output}
            headers = {'content-type': 'application/json'}
            response = requests.request(method, url, data=json.dumps(data), headers=headers)
            if response.status_code != 200:
                response.raise_for_status()
        except Exception as e:
            LOG.error(e)
