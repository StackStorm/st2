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

from __future__ import absolute_import
import ast
import copy
import json
import re
import retrying
import six

from oslo_config import cfg
from mistralclient.api import client as mistral

from st2common.constants import action as action_constants
from st2common import log as logging
from st2common.callback import base as callback
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
    action_constants.LIVEACTION_STATUS_PENDING: 'PAUSED',
    action_constants.LIVEACTION_STATUS_CANCELING: 'CANCELLED',
    action_constants.LIVEACTION_STATUS_CANCELED: 'CANCELLED',
    action_constants.LIVEACTION_STATUS_PAUSING: 'PAUSED',
    action_constants.LIVEACTION_STATUS_PAUSED: 'PAUSED',
    action_constants.LIVEACTION_STATUS_RESUMING: 'RUNNING'
}

MISTRAL_ACCEPTED_STATES = copy.deepcopy(action_constants.LIVEACTION_COMPLETED_STATES)
MISTRAL_ACCEPTED_STATES += [action_constants.LIVEACTION_STATUS_PAUSED]


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
    def _update_action_execution(cls, url, data):
        action_execution_id = get_action_execution_id_from_url(url)

        LOG.info('Sending callback to %s with data %s.', url, data)

        client = mistral.client(
            mistral_url=cfg.CONF.mistral.v2_base_url,
            username=cfg.CONF.mistral.keystone_username,
            api_key=cfg.CONF.mistral.keystone_password,
            project_name=cfg.CONF.mistral.keystone_project_name,
            auth_url=cfg.CONF.mistral.keystone_auth_url,
            cacert=cfg.CONF.mistral.cacert,
            insecure=cfg.CONF.mistral.insecure)

        client.action_executions.update(action_execution_id, **data)

    @classmethod
    def _encode(cls, value):
        if isinstance(value, dict):
            return {k: cls._encode(v) for k, v in six.iteritems(value)}
        elif isinstance(value, list):
            return [cls._encode(item) for item in value]
        elif isinstance(value, six.string_types) and not six.PY3:
            try:
                value = value.decode('utf-8')
            except Exception:
                LOG.exception('Unable to decode value to utf-8.')

            try:
                value = value.encode('unicode_escape')
            except Exception:
                LOG.exception('Unable to unicode escape value.')

            return value
        else:
            return value

    @classmethod
    def callback(cls, liveaction):
        assert isinstance(liveaction.callback, dict)
        assert 'url' in liveaction.callback

        url = liveaction.callback['url']
        status = liveaction.status
        result = liveaction.result

        if status not in MISTRAL_ACCEPTED_STATES:
            LOG.warning('Unable to callback %s because status "%s" is not supported.', url, status)
            return

        try:
            if isinstance(result, six.string_types) and len(result) > 0 and result[0] in ['{', '[']:
                value = ast.literal_eval(result)
                if type(value) in [dict, list]:
                    result = value

            result = cls._encode(result)
            output = json.dumps(result) if type(result) in [dict, list] else str(result)
            output = output.replace('\\\\\\\\u', '\\\\u')
            data = {'state': STATUS_MAP[status], 'output': output}

            cls._update_action_execution(url, data)
        except Exception as e:
            LOG.exception(e)
