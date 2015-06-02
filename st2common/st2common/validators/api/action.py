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

from st2common.exceptions.apivalidation import ValueValidationException
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common import log as logging
from st2common.util.action_db import get_runnertype_by_name
from st2common.content.utils import get_packs_path
from st2common.content.utils import check_pack_content_directory_exists


LOG = logging.getLogger(__name__)


def validate_action(action_api):
    runner_db = _get_runner_model(action_api)

    # Check if pack is valid.
    if not _is_valid_pack(action_api.pack):
        packs_base_path = get_packs_path()
        msg = ('Content pack "%s" is not found or doesn\'t contain actions directory. '
               'Searched in: %s' %
               (action_api.pack, packs_base_path))
        raise ValueValidationException(msg)

    # Check if parameters defined are valid.
    _validate_parameters(action_api.parameters, runner_db.runner_parameters)


def _get_runner_model(action_api):
    runner_db = None
    # Check if runner exists.
    try:
        runner_db = get_runnertype_by_name(action_api.runner_type)
    except StackStormDBObjectNotFoundError:
        msg = 'RunnerType %s is not found.' % action_api.runner_type
        raise ValueValidationException(msg)
    return runner_db


def _is_valid_pack(pack):
    return check_pack_content_directory_exists(pack=pack, content_type='actions')


def _validate_parameters(action_params=None, runner_params=None):
    for param, action_param_meta in six.iteritems(action_params):
        if 'immutable' in action_param_meta:
            if param in runner_params:
                runner_param_meta = runner_params[param]
                if 'immutable' in runner_param_meta:
                    msg = 'Param %s is declared immutable in runner. ' % param + \
                          'Cannot override in action.'
                    raise ValueValidationException(msg)
                if 'default' not in action_param_meta and 'default' not in runner_param_meta:
                    msg = 'Immutable param %s requires a default value.' % param
                    raise ValueValidationException(msg)
            else:
                if 'default' not in action_param_meta:
                    msg = 'Immutable param %s requires a default value.' % param
                    raise ValueValidationException(msg)
