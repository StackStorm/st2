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

import mongoengine as me

from st2common.fields import ComplexDateTimeField
from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.util import date as date_utils
from st2common.constants.rule_enforcement import RULE_ENFORCEMENT_STATUS_SUCCEEDED
from st2common.constants.rule_enforcement import RULE_ENFORCEMENT_STATUS_FAILED

__all__ = ["RuleReferenceSpecDB", "RuleEnforcementDB"]


class RuleReferenceSpecDB(me.EmbeddedDocument):
    ref = me.StringField(unique=False, help_text="Reference to rule.", required=True)
    id = me.StringField(required=False, help_text="Rule ID.")
    uid = me.StringField(required=True, help_text="Rule UID.")

    def __str__(self):
        result = []
        result.append("RuleReferenceSpecDB@")
        result.append(str(id(self)))
        result.append('(ref="%s", ' % self.ref)
        result.append('id="%s", ' % self.id)
        result.append('uid="%s")' % self.uid)

        return "".join(result)


class RuleEnforcementDB(stormbase.StormFoundationDB, stormbase.TagsMixin):
    UID_FIELDS = ["id"]

    trigger_instance_id = me.StringField(required=True)
    execution_id = me.StringField(required=False)
    failure_reason = me.StringField(required=False)
    rule = me.EmbeddedDocumentField(RuleReferenceSpecDB, required=True)
    enforced_at = ComplexDateTimeField(
        default=date_utils.get_datetime_utc_now,
        help_text="The timestamp when the rule enforcement happened.",
    )
    status = me.StringField(
        required=True,
        default=RULE_ENFORCEMENT_STATUS_SUCCEEDED,
        help_text="Rule enforcement status.",
    )

    meta = {
        "indexes": [
            {"fields": ["trigger_instance_id"]},
            {"fields": ["execution_id"]},
            {"fields": ["rule.id"]},
            {"fields": ["rule.ref"]},
            {"fields": ["enforced_at"]},
            {"fields": ["-enforced_at"]},
            {"fields": ["-enforced_at", "rule.ref"]},
            {"fields": ["status"]},
        ]
        + stormbase.TagsMixin.get_indexes()
    }

    def __init__(self, *args, **values):
        super(RuleEnforcementDB, self).__init__(*args, **values)

        # Set status to succeeded for old / existing RuleEnforcementDB which predate status field
        status = getattr(self, "status", None)
        failure_reason = getattr(self, "failure_reason", None)

        if status in [None, RULE_ENFORCEMENT_STATUS_SUCCEEDED] and failure_reason:
            self.status = RULE_ENFORCEMENT_STATUS_FAILED

    # NOTE: Note the following method is exposed so loggers in rbac resolvers can log objects
    # with a consistent get_uid interface.
    def get_uid(self):
        # TODO Construct uid from non id field:
        uid = [self.RESOURCE_TYPE, str(self.id)]  # pylint: disable=E1101
        return ":".join(uid)


rule_enforcement_access = MongoDBAccess(RuleEnforcementDB)

MODELS = [RuleEnforcementDB]
