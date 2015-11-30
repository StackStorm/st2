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

import mongoengine as me

from st2common.fields import ComplexDateTimeField
from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.util import date as date_utils


class RuleEnforcementDB(stormbase.StormFoundationDB, stormbase.TagsMixin):
    trigger_instance_id = me.StringField(required=True)
    execution_id = me.StringField(required=False)
    timestamp = ComplexDateTimeField(
        default=date_utils.get_datetime_utc_now,
        help_text='The timestamp when the rule enforcement was created.')

rule_enforcement_access = MongoDBAccess(RuleEnforcementDB)

MODELS = [RuleEnforcementDB]
