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
import re
import retrying

from oslo_config import cfg

from st2common.constants import action as action_constants
from st2common import log as logging
from st2common.callback import base as callback
from st2common.persistence.execution import ActionExecution
from st2common.util import url as url_utils
from st2common.util.workflow import mistral as utils


LOG = logging.getLogger(__name__)


STATUS_MAP = {
    action_constants.LIVEACTION_STATUS_REQUESTED: 'RUNNING',
    action_constants.LIVEACTION_STATUS_SCHEDULED: 'RUNNING',
    action_constants.LIVEACTION_STATUS_DELAYED: 'RUNNING',
    action_constants.LIVEACTION_STATUS_RUNNING: 'RUNNING',
    action_constants.LIVEACTION_STATUS_SUCCEEDED: 'SUCCESS',
    action_constants.LIVEACTION_STATUS_FAILED: 'ERROR',
    action_constants.LIVEACTION_STATUS_TIMED_OUT: 'ERROR',
    action_constants.LIVEACTION_STATUS_ABANDONED: 'ERROR',
    action_constants.LIVEACTION_STATUS_CANCELING: 'RUNNING',
    action_constants.LIVEACTION_STATUS_CANCELED: 'CANCELLED'
}


def get_instance():
    return MistralCallbackHandler


def get_action_execution_id_from_url(url):
    match = re.search('(.+)/action_executions/(.+)', url)
    if not match or len(match.groups()) != 2:
        raise ValueError('Unable to extract the action execution ID '
                         'from the callback URL (%s).' % (url))

    return match.group(2)


class MistralCallbackHandler(callback.AsyncActionExecutionCallbackHandler):

    @classmethod
    @retrying.retry(
        retry_on_exception=utils.retry_on_exceptions,
        wait_exponential_multiplier=cfg.CONF.mistral.retry_exp_msec,
        wait_exponential_max=cfg.CONF.mistral.retry_exp_max_msec,
        stop_max_delay=cfg.CONF.mistral.retry_stop_max_msec)
    def _update_action_execution(cls, url, data, auth_token):
        action_execution_id = get_action_execution_id_from_url(url)

        LOG.info('Sending callback to %s with data %s.', url, data)

        base_url = url_utils.get_url_without_trailing_slash(cfg.CONF.mistral.v2_base_url)
        client = utils.get_client(base_url, auth_token=auth_token)
        client.action_executions.update(action_execution_id, **data)

    @classmethod
    def callback(cls, url, context, status, result):
        if status not in action_constants.LIVEACTION_COMPLETED_STATES:
            return

        parent_ex_id = context['parent']['execution_id']
        parent_ex = ActionExecution.get_by_id(parent_ex_id)
        parent_ex_ctx = parent_ex.context
        mistral_ctx = parent_ex_ctx.get('mistral', {})
        auth_token = mistral_ctx.get('auth_token', None)

        try:
            if isinstance(result, basestring) and len(result) > 0 and result[0] in ['{', '[']:
                value = ast.literal_eval(result)
                if type(value) in [dict, list]:
                    result = value

            output = json.dumps(result) if type(result) in [dict, list] else str(result)
            data = {'state': STATUS_MAP[status], 'output': output}

            cls._update_action_execution(url, data, auth_token)
        except Exception as e:
            LOG.exception(e)
