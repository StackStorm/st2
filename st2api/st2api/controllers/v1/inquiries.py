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

import copy
import json

import six
from oslo_config import cfg
from six.moves import http_client

from st2api.controllers.resource import ResourceController
from st2api.controllers.v1 import execution_views
from st2common.constants import action as action_constants
from st2common.exceptions import db as db_exceptions
from st2common.exceptions import rbac as rbac_exceptions
from st2common import log as logging
from st2common.models.api import inquiry as inqy_api_models
from st2common.persistence import execution as ex_db_access
from st2common.rbac import types as rbac_types
from st2common.rbac.backends import get_rbac_backend
from st2common import router as api_router
from st2common.services import inquiry as inquiry_service


__all__ = [
    'InquiriesController'
]

LOG = logging.getLogger(__name__)

INQUIRY_RUNNER = 'inquirer'


class InquiriesController(ResourceController):
    """
    API controller for Inquiries
    """

    supported_filters = copy.deepcopy(execution_views.SUPPORTED_FILTERS)

    # No data model currently exists for Inquiries, so we're "borrowing" ActionExecutions
    # for the DB layer
    model = inqy_api_models.InquiryAPI
    access = ex_db_access.ActionExecution

    def get_all(self, exclude_attributes=None, include_attributes=None, requester_user=None,
                limit=None, **raw_filters):
        """Retrieve multiple Inquiries

            Handles requests:
                GET /inquiries/
        """

        # NOTE: This controller retrieves execution objects and returns a new model composed of
        # execution.result fields and that's why we pass empty value for include_fields and
        # exclude_fields.
        # We only need to retrieve "id" and "result" from database and perform actual field
        # filtering before returning the response.
        raw_inquiries = super(InquiriesController, self)._get_all(
            exclude_fields=[],
            include_fields=['id', 'result'],
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
        inquiries = [
            inqy_api_models.InquiryResponseAPI.from_model(raw_inquiry, skip_db=True)
            for raw_inquiry in json.loads(raw_inquiries.body)
        ]

        # Repackage into Response with correct headers
        resp = api_router.Response(json=inquiries)
        resp.headers['X-Total-Count'] = raw_inquiries.headers['X-Total-Count']

        if limit:
            resp.headers['X-Limit'] = str(limit)

        return resp

    def get_one(self, inquiry_id, requester_user=None):
        """Retrieve a single Inquiry

            Handles requests:
                GET /inquiries/<inquiry id>
        """

        # Retrieve the inquiry by id.
        # (Passing permission_type here leverages inquiry service built-in RBAC assertions)
        try:
            inquiry = self._get_one_by_id(
                id=inquiry_id,
                requester_user=requester_user,
                permission_type=rbac_types.PermissionType.INQUIRY_VIEW
            )
        except db_exceptions.StackStormDBObjectNotFoundError as e:
            LOG.exception('Unable to identify inquiry with id "%s".' % inquiry_id)
            api_router.abort(http_client.NOT_FOUND, six.text_type(e))
        except rbac_exceptions.ResourceAccessDeniedError as e:
            LOG.exception('User is denied access to inquiry "%s".' % inquiry_id)
            api_router.abort(http_client.FORBIDDEN, six.text_type(e))
        except Exception as e:
            LOG.exception('Unable to get record for inquiry "%s".' % inquiry_id)
            api_router.abort(http_client.INTERNAL_SERVER_ERROR, six.text_type(e))

        try:
            inquiry_service.check_inquiry(inquiry)
        except Exception as e:
            api_router.abort(http_client.BAD_REQUEST, six.text_type(e))

        return inqy_api_models.InquiryResponseAPI.from_inquiry_api(inquiry)

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

        # Set requester to system user if not provided.
        if not requester_user:
            requester_user = cfg.CONF.system_user.user

        # Retrieve the inquiry by id.
        try:
            inquiry = self._get_one_by_id(
                id=inquiry_id,
                requester_user=requester_user,
                permission_type=rbac_types.PermissionType.INQUIRY_RESPOND
            )
        except db_exceptions.StackStormDBObjectNotFoundError as e:
            LOG.exception('Unable to identify inquiry with id "%s".' % inquiry_id)
            api_router.abort(http_client.NOT_FOUND, six.text_type(e))
        except rbac_exceptions.ResourceAccessDeniedError as e:
            LOG.exception('User is denied access to inquiry "%s".' % inquiry_id)
            api_router.abort(http_client.FORBIDDEN, six.text_type(e))
        except Exception as e:
            LOG.exception('Unable to get record for inquiry "%s".' % inquiry_id)
            api_router.abort(http_client.INTERNAL_SERVER_ERROR, six.text_type(e))

        # Check if inquiry can still be respond to.
        try:
            inquiry_service.check_inquiry(inquiry)
        except Exception as e:
            LOG.exception('Fail checking validity of inquiry "%s".' % inquiry_id)
            api_router.abort(http_client.BAD_REQUEST, six.text_type(e))

        # Check if user has permission to respond to this inquiry.
        try:
            inquiry_service.check_permission(inquiry, requester_user)
        except Exception as e:
            LOG.exception('Fail checking permission for inquiry "%s".' % inquiry_id)
            api_router.abort(http_client.FORBIDDEN, six.text_type(e))

        # Validate the body of the response against the schema parameter for this inquiry.
        try:
            inquiry_service.validate_response(inquiry, response_data.response)
        except Exception as e:
            LOG.exception('Fail checking response for inquiry "%s".' % inquiry_id)
            api_router.abort(http_client.BAD_REQUEST, six.text_type(e))

        # Respond to inquiry and update if there is a partial response.
        try:
            inquiry_service.respond(inquiry, response_data.response, requester=requester_user)
        except Exception as e:
            LOG.exception('Fail to update response for inquiry "%s".' % inquiry_id)
            api_router.abort(http_client.INTERNAL_SERVER_ERROR, six.text_type(e))

        return {
            'id': inquiry_id,
            'response': response_data.response
        }

    def _get_one_by_id(self, id, requester_user, permission_type,
                       exclude_fields=None, from_model_kwargs=None):
        """Override ResourceController._get_one_by_id to contain scope of Inquiries UID hack
        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        """
        LOG.debug('Retrieving action execution for inquiry "%s".' % id)

        execution_db = self._get_by_id(resource_id=id, exclude_fields=exclude_fields)

        if not execution_db:
            raise db_exceptions.StackStormDBObjectNotFoundError()

        # Inquiry currently does not have it's own database model and share with ActionExecution.
        # The object uid is in the format of "execution:<id>". To allow RBAC to resolve correctly
        # for inquiries, we're overriding the "get_uid" function so the object uid can be set to
        # "inquiry:<id>".
        #
        # TODO (mierdin): All of this should be removed once Inquiries get their own DB model.
        if (execution_db and getattr(execution_db, 'runner', None) and
                execution_db.runner.get('runner_module') == INQUIRY_RUNNER):
            execution_db.get_uid = get_uid

        LOG.debug('Checking permission on inquiry "%s".' % id)

        if permission_type:
            rbac_utils = get_rbac_backend().get_utils_class()
            rbac_utils.assert_user_has_resource_db_permission(
                user_db=requester_user,
                resource_db=execution_db,
                permission_type=permission_type
            )

        from_model_kwargs = from_model_kwargs or {}
        from_model_kwargs.update(self.from_model_kwargs)
        result = self.model.from_model(execution_db, **from_model_kwargs)

        return result


def get_uid():
    """Inquiry UID hack for RBAC
    """
    return 'inquiry'


inquiries_controller = InquiriesController()
