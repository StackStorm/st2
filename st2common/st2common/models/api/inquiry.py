# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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

from st2common.constants.action import LIVEACTION_STATUSES
from st2common.models.api.base import BaseAPI
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, LiveActionAPI
from st2common.models.db.execution import ActionExecutionDB
from st2common import log as logging


LOG = logging.getLogger(__name__)

REQUIRED_ATTR_SCHEMAS = {
    "action": copy.deepcopy(ActionAPI.schema),
    "runner": copy.deepcopy(RunnerTypeAPI.schema),
    "liveaction": copy.deepcopy(LiveActionAPI.schema),
}

for k, v in six.iteritems(REQUIRED_ATTR_SCHEMAS):
    v.update({"required": True})


class InquiryAPI(BaseAPI):
    """Model for working with Inquiries within the API controller

    Please see InquiryResponseAPI for a model more appropriate for API
    responses. This model contains fields that do not comply with the API
    spec.
    """

    # Inquiries don't have their own database model, since (right now) they are just
    # ActionExecutions with a "pending" status. The "from_model" function will serve
    # to transform the relevant fields to a new InquiryAPI instance
    model = ActionExecutionDB

    schema = {
        "title": "Inquiry",
        "description": "Record of an Inquiry",
        "type": "object",
        "properties": {
            "id": {"type": "string", "required": True},
            "route": {"type": "string", "default": "", "required": True},
            "ttl": {"type": "integer", "default": 1440, "required": True},
            "users": {"type": "array", "default": [], "required": True},
            "roles": {"type": "array", "default": [], "required": True},
            "schema": {
                "type": "object",
                "default": {
                    "title": "response_data",
                    "type": "object",
                    "properties": {
                        "continue": {
                            "type": "boolean",
                            "description": "Would you like to continue the workflow?",
                            "required": True,
                        }
                    },
                },
                "required": True,
            },
            "liveaction": REQUIRED_ATTR_SCHEMAS["liveaction"],
            "runner": REQUIRED_ATTR_SCHEMAS["runner"],
            "status": {
                "description": "The current status of the action execution.",
                "type": "string",
                "enum": LIVEACTION_STATUSES,
            },
            "parent": {"type": "string"},
            "result": {
                "anyOf": [
                    {"type": "array"},
                    {"type": "boolean"},
                    {"type": "integer"},
                    {"type": "number"},
                    {"type": "object"},
                    {"type": "string"},
                ]
            },
        },
        "additionalProperties": False,
    }

    skip_unescape_field_names = [
        "result",
    ]

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        doc = cls._from_model(model, mask_secrets=mask_secrets)

        doc["result"] = ActionExecutionDB.result.parse_field_value(doc["result"])

        newdoc = {
            "id": doc["id"],
            "runner": doc.get("runner", None),
            "status": doc.get("status", None),
            "liveaction": doc.get("liveaction", None),
            "parent": doc.get("parent", None),
            "result": doc.get("result", None),
        }

        for field in ["route", "ttl", "users", "roles", "schema"]:
            newdoc[field] = doc["result"].get(field, None)

        return cls(**newdoc)


class InquiryResponseAPI(BaseAPI):
    """A more pruned Inquiry model, containing only the fields needed for an API response"""

    model = ActionExecutionDB
    schema = {
        "title": "Inquiry",
        "description": "Record of an Inquiry",
        "type": "object",
        "properties": {
            "id": {"type": "string", "required": True},
            "route": {"type": "string", "default": "", "required": True},
            "ttl": {"type": "integer", "default": 1440, "required": True},
            "users": {"type": "array", "default": [], "required": True},
            "roles": {"type": "array", "default": [], "required": True},
            "schema": {
                "type": "object",
                "default": {
                    "title": "response_data",
                    "type": "object",
                    "properties": {
                        "continue": {
                            "type": "boolean",
                            "description": "Would you like to continue the workflow?",
                            "required": True,
                        }
                    },
                },
                "required": True,
            },
        },
        "additionalProperties": False,
    }

    @classmethod
    def from_model(cls, model, mask_secrets=False, skip_db=False):
        """Create InquiryResponseAPI instance from model

        Allows skipping the BaseAPI._from_model function if you already
        have a properly formed dict and just need to prune it

        :param skip_db: Skip the parent class' _from_model function call
        :rtype: InquiryResponseAPI
        """

        if not skip_db:
            doc = cls._from_model(model, mask_secrets=mask_secrets)
        else:
            doc = model

        newdoc = {"id": doc["id"]}
        for field in ["route", "ttl", "users", "roles", "schema"]:
            newdoc[field] = doc["result"].get(field)

        return cls(**newdoc)

    @classmethod
    def from_inquiry_api(cls, inquiry_api, mask_secrets=False):
        """Allows translation of InquiryAPI directly to InquiryResponseAPI

        This bypasses the DB modeling, since there's no DB model for Inquiries yet.
        """

        return cls(
            id=getattr(inquiry_api, "id", None),
            route=getattr(inquiry_api, "route", None),
            ttl=getattr(inquiry_api, "ttl", None),
            users=getattr(inquiry_api, "users", None),
            roles=getattr(inquiry_api, "roles", None),
            schema=getattr(inquiry_api, "schema", None),
        )
