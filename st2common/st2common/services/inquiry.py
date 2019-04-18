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

import copy
import six

from oslo_config import cfg

from st2actions.container import base as container
from st2common.models.db import auth as auth_db_models
from st2common.constants import action as action_constants
from st2common.exceptions import inquiry as inquiry_exceptions
from st2common import log as logging
from st2common.persistence import liveaction as lv_db_access
from st2common.services import action as action_service
from st2common.services import executions as execution_service
from st2common.services import workflows as workflow_service
from st2common.rbac.backends import get_rbac_backend
from st2common.util import action_db as action_utils
from st2common.util import date as date_utils
from st2common.util import schema as schema_utils
from st2common.util import system_info as sys_info_utils


LOG = logging.getLogger(__name__)


def check_inquiry(inquiry):
    LOG.debug('Checking action execution "%s" to see if is an inquiry.' % str(inquiry.id))

    if inquiry.runner.get('name') != 'inquirer':
        raise inquiry_exceptions.InvalidInquiryInstance(str(inquiry.id))

    LOG.debug('Checking if the inquiry "%s" has timed out.' % str(inquiry.id))

    if inquiry.status == action_constants.LIVEACTION_STATUS_TIMED_OUT:
        raise inquiry_exceptions.InquiryTimedOut(str(inquiry.id))

    LOG.debug('Checking if the inquiry "%s" is responded.' % str(inquiry.id))

    if inquiry.status != action_constants.LIVEACTION_STATUS_PENDING:
        raise inquiry_exceptions.InquiryAlreadyResponded(str(inquiry.id))


def check_permission(inquiry, requester):
    # Normalize user object.
    user_db = (
        auth_db_models.UserDB(requester)
        if isinstance(requester, six.string_types)
        else requester
    )

    # Deny by default
    roles_passed = False
    users_passed = False

    # Determine role-level permissions
    roles = getattr(inquiry, 'roles', [])

    if not roles:
        # No roles definition so we treat it as a pass
        roles_passed = True

    for role in roles:
        rbac_utils = get_rbac_backend().get_utils_class()
        user_has_role = rbac_utils.user_has_role(user_db, role)

        LOG.debug('Checking user %s is in role %s - %s' % (user_db, role, user_has_role))

        if user_has_role:
            roles_passed = True
            break

    # Determine user-level permissions
    users = getattr(inquiry, 'users', [])
    if not users or user_db.name in users:
        users_passed = True

    # Thow exception if either permission check failed.
    if not roles_passed or not users_passed:
        raise inquiry_exceptions.InquiryResponseUnauthorized(str(inquiry.id), requester)


def validate_response(inquiry, response):
    schema = inquiry.schema

    LOG.debug('Validating inquiry response: %s against schema: %s' % (response, schema))

    try:
        schema_utils.validate(
            instance=response,
            schema=schema,
            cls=schema_utils.CustomValidator,
            use_default=True,
            allow_default_none=True
        )
    except Exception as e:
        msg = 'Response for inquiry "%s" did not pass schema validation.'
        LOG.exception(msg % str(inquiry.id))
        raise inquiry_exceptions.InvalidInquiryResponse(str(inquiry.id), six.text_type(e))


def respond(inquiry, response, requester=None):
    # Set requester to system user is not provided.
    if not requester:
        requester = cfg.CONF.system_user.user

    # Retrieve the liveaction from the database.
    liveaction_db = lv_db_access.LiveAction.get_by_id(inquiry.liveaction.get('id'))

    # Resume the parent workflow first. If the action execution for the inquiry is updated first,
    # it triggers handling of the action execution completion which will interact with the paused
    # parent workflow. The resuming logic that is executed here will then race with the completion
    # of the inquiry action execution, which will randomly result in the parent workflow stuck in
    # paused state.
    if liveaction_db.context.get('parent'):
        LOG.debug('Resuming workflow parent(s) for inquiry "%s".' % str(inquiry.id))

        # For action execution under Action Chain and Mistral workflows, request the entire
        # workflow to resume. Orquesta handles resume differently and so does not require root
        # to resume. Orquesta allows for specifc branches to resume while other is paused. When
        # there is no other paused branches, the conductor will resume the rest of the workflow.
        resume_target = (
            action_service.get_parent_liveaction(liveaction_db)
            if workflow_service.is_action_execution_under_workflow_context(liveaction_db)
            else action_service.get_root_liveaction(liveaction_db)
        )

        if resume_target.status in action_constants.LIVEACTION_PAUSE_STATES:
            action_service.request_resume(resume_target, requester)

    # Succeed the liveaction and update result with the inquiry response.
    LOG.debug('Updating response for inquiry "%s".' % str(inquiry.id))

    result = copy.deepcopy(inquiry.result)
    result['response'] = response

    liveaction_db = action_utils.update_liveaction_status(
        status=action_constants.LIVEACTION_STATUS_SUCCEEDED,
        end_timestamp=date_utils.get_datetime_utc_now(),
        runner_info=sys_info_utils.get_process_info(),
        result=result,
        liveaction_id=str(liveaction_db.id)
    )

    # Sync the liveaction with the corresponding action execution.
    execution_service.update_execution(liveaction_db)

    # Invoke inquiry post run to trigger a callback to parent workflow.
    LOG.debug('Invoking post run for inquiry "%s".' % str(inquiry.id))
    runner_container = container.get_runner_container()
    action_db = action_utils.get_action_by_ref(liveaction_db.action)
    runnertype_db = action_utils.get_runnertype_by_name(action_db.runner_type['name'])
    runner = runner_container._get_runner(runnertype_db, action_db, liveaction_db)
    runner.post_run(status=action_constants.LIVEACTION_STATUS_SUCCEEDED, result=result)

    return liveaction_db
