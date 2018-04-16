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

import json
from oslo_config import cfg

import copy

from six.moves import http_client
from st2common.models.db.auth import UserDB
from st2api.controllers.resource import ResourceController
from st2api.controllers.v1.executionviews import SUPPORTED_FILTERS
from st2common import log as logging
from st2common.util import action_db as action_utils
from st2common.util import schema as util_schema
from st2common.util import system_info
from st2common.services import executions
from st2common.constants import action as action_constants
from st2common.rbac.types import PermissionType
from st2common.rbac import utils as rbac_utils
from st2common.router import abort
from st2common.router import Response
from st2common.models.api.inquiry import InquiryAPI, InquiryResponseAPI
from st2common.persistence.execution import ActionExecution
from st2common.services import action as action_service
from st2common.util.action_db import (get_action_by_ref, get_runnertype_by_name)

from st2actions.container.base import get_runner_container

__all__ = [
    'InquiriesController'
]

LOG = logging.getLogger(__name__)
INQUIRY_RUNNER = 'inquirer'


class InquiriesController(ResourceController):
    """API controller for Inquiries
    """

    supported_filters = copy.deepcopy(SUPPORTED_FILTERS)

    # No data model currently exists for Inquiries, so we're "borrowing" ActionExecutions
    # for the DB layer
    model = InquiryAPI
    access = ActionExecution

    def get_all(self, requester_user=None, limit=None, **raw_filters):
        """Retrieve multiple Inquiries

            Handles requests:
                GET /inquiries/
        """

        raw_inquiries = super(InquiriesController, self)._get_all(
            limit=limit,
            raw_filters={
                'status': action_constants.LIVEACTION_STATUS_PENDING,
                'runner': INQUIRY_RUNNER
            },
            requester_user=requester_user
        )

        # Since "model" is set to InquiryAPI (for good reasons), _get_all returns a list of
        # InquiryAPI instances, already converted to JSON. So in order to convert these to
        # InquiryResponseAPI instances, we first have to convert raw_inquiries.body back to
        # a list of dicts, and then individually convert these to InquiryResponseAPI instances
        inquiries = [InquiryResponseAPI.from_model(raw_inquiry, skip_db=True)
                     for raw_inquiry in json.loads(raw_inquiries.body)]

        # Repackage into Response with correct headers
        resp = Response(json=inquiries)
        resp.headers['X-Total-Count'] = raw_inquiries.headers['X-Total-Count']
        if limit:
            resp.headers['X-Limit'] = str(limit)
        return resp

    def get_one(self, inquiry_id, requester_user=None):
        """Retrieve a single Inquiry

            Handles requests:
                GET /inquiries/<inquiry id>
        """

        # Retrieve the desired inquiry
        #
        # (Passing permission_type here leverages _get_one_by_id's built-in
        # RBAC assertions)
        inquiry = self._get_one_by_id(
            id=inquiry_id,
            requester_user=requester_user,
            permission_type=PermissionType.INQUIRY_VIEW
        )

        sanity_result, msg = self._inquiry_sanity_check(inquiry)
        if not sanity_result:
            abort(http_client.BAD_REQUEST, msg)

        return InquiryResponseAPI.from_inquiry_api(inquiry)

    def put(self, inquiry_id, response_data, requester_user):
        """Provide response data to an Inquiry

            In general, provided the response data validates against the provided
            schema, and the user has the appropriate permissions to respond,
            this will set the Inquiry execution to a successful status, and resume
            the parent workflow.

            Handles requests:
                PUT /inquiries/<inquiry id>
        """

        LOG.debug("Inquiry %s received response payload: %s" % (inquiry_id, response_data.response))

        # Retrieve details of the inquiry via ID (i.e. params like schema)
        inquiry = self._get_one_by_id(
            id=inquiry_id,
            requester_user=requester_user,
            permission_type=PermissionType.INQUIRY_RESPOND
        )

        sanity_result, msg = self._inquiry_sanity_check(inquiry)
        if not sanity_result:
            abort(http_client.BAD_REQUEST, msg)

        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)

        # Determine permission of this user to respond to this Inquiry
        if not self._can_respond(inquiry, requester_user):
            abort(
                http_client.FORBIDDEN,
                'Requesting user does not have permission to respond to inquiry %s.' % inquiry_id
            )

        # Validate the body of the response against the schema parameter for this inquiry
        schema = inquiry.schema
        LOG.debug("Validating inquiry response: %s against schema: %s" %
                  (response_data.response, schema))
        try:
            util_schema.validate(instance=response_data.response, schema=schema,
                                 cls=util_schema.CustomValidator, use_default=True,
                                 allow_default_none=True)
        except Exception as e:
            LOG.debug("Failed to validate response data against provided schema: %s" % e.message)
            abort(http_client.BAD_REQUEST, 'Response did not pass schema validation.')

        # Update inquiry for completion
        new_result = copy.deepcopy(inquiry.result)
        new_result["response"] = response_data.response
        liveaction_db = self._mark_inquiry_complete(
            inquiry.liveaction.get('id'),
            new_result
        )

        # We only want to request a workflow resume if this has a parent
        if liveaction_db.context.get("parent"):

            # Request that root workflow resumes
            root_liveaction = action_service.get_root_liveaction(liveaction_db)
            action_service.request_resume(
                root_liveaction,
                requester_user
            )

        return {
            "id": inquiry_id,
            "response": response_data.response
        }

    def _inquiry_sanity_check(self, inquiry_candidate):
        """Sanity checks for ensuring that a retrieved execution is indeed an Inquiry

        It must use the "inquirer" runner, and it must currently be in a "pending" status

        :param inquiry_candidate: The inquiry to check

        :rtype: bool - True if a valid Inquiry. False if not.
        :rtype: str - Error message, if any
        """

        if inquiry_candidate.runner.get('name') != 'inquirer':
            return (False, '%s is not an Inquiry.' % inquiry_candidate.id)

        if inquiry_candidate.status == action_constants.LIVEACTION_STATUS_TIMED_OUT:
            return (
                False,
                'Inquiry %s timed out and can no longer be responded to' % inquiry_candidate.id
            )

        if inquiry_candidate.status != action_constants.LIVEACTION_STATUS_PENDING:
            return (False, 'Inquiry %s has already been responded to' % inquiry_candidate.id)

        return (True, "")

    def _mark_inquiry_complete(self, inquiry_id, result):
        """Mark Inquiry as completed

        This function updates the local LiveAction and Execution with a successful
        status as well as call the "post_run" function for the Inquirer runner so that
        the appropriate callback function is executed

        :param inquiry: The Inquiry for which the response is given
        :param requester_user: The user providing the response

        :rtype: bool - True if requester_user is able to respond. False if not.
        """

        # Update inquiry's execution result with a successful status and the validated response
        liveaction_db = action_utils.update_liveaction_status(
            status=action_constants.LIVEACTION_STATUS_SUCCEEDED,
            runner_info=system_info.get_process_info(),
            result=result,
            liveaction_id=inquiry_id)
        executions.update_execution(liveaction_db)

        # Call Inquiry runner's post_run to trigger callback to workflow
        runner_container = get_runner_container()
        action_db = get_action_by_ref(liveaction_db.action)
        runnertype_db = get_runnertype_by_name(action_db.runner_type['name'])
        runner = runner_container._get_runner(runnertype_db, action_db, liveaction_db)
        runner.post_run(status=action_constants.LIVEACTION_STATUS_SUCCEEDED, result=result)

        return liveaction_db

    def _can_respond(self, inquiry, requester_user):
        """Determine if requester_user is permitted to respond based on parameters

        This determines if the requesting user has permission to respond to THIS inquiry.
        Note this is NOT RBAC, and you should still protect the API endpoint with RBAC
        where appropriate.

        :param inquiry: The Inquiry for which the response is given
        :param requester_user: The user providing the response

        :rtype: bool - True if requester_user is able to respond. False if not.
        """

        # Deny by default
        roles_passed = False
        users_passed = False

        # Determine role-level permissions
        roles = getattr(inquiry, 'roles', [])

        if not roles:
            # No roles definition so we treat it as a pass
            roles_passed = True

        for role in roles:
            LOG.debug("Checking user %s is in role %s - %s" % (
                requester_user, role, rbac_utils.user_has_role(requester_user, role))
            )

            if rbac_utils.user_has_role(requester_user, role):
                roles_passed = True
                break

        # Determine user-level permissions
        users = getattr(inquiry, 'users', [])
        if not users or requester_user.name in users:
            users_passed = True

        # Both must pass
        return roles_passed and users_passed

    def _get_one_by_id(self, id, requester_user, permission_type, exclude_fields=None,
                       from_model_kwargs=None):
        """Override ResourceController._get_one_by_id to contain scope of Inquiries UID hack

        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        """

        instance = self._get_by_id(resource_id=id, exclude_fields=exclude_fields)

        # _get_by_id pulls the resource by ID directly off of the database. Since
        # Inquiries don't have their own DB model yet, this comes in the format
        # "execution:<id>". So, to allow RBAC to get a handle on inquiries specifically,
        # we're overriding the "get_uid" function to return one specific to Inquiries.
        #
        # TODO (mierdin): All of this should be removed once Inquiries get their own DB model
        if getattr(instance, 'runner', None) and instance.runner.get('runner_module') == 'inquirer':
            def get_uid():
                return "inquiry"
            instance.get_uid = get_uid

        if permission_type:
            rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                              resource_db=instance,
                                                              permission_type=permission_type)

        if not instance:
            msg = 'Unable to identify resource with id "%s".' % id
            abort(http_client.NOT_FOUND, msg)

        from_model_kwargs = from_model_kwargs or {}
        from_model_kwargs.update(self.from_model_kwargs)
        result = self.model.from_model(instance, **from_model_kwargs)

        return result


inquiries_controller = InquiriesController()
