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

from st2common.constants import action as ac_const
from st2common import log as logging
from st2common.persistence import policy as pc_db_access
from st2common import policies as engine


LOG = logging.getLogger(__name__)


def apply_pre_run_policies(lv_ac_db):
    LOG.debug('Applying pre-run policies for liveaction "%s".' % str(lv_ac_db.id))

    policy_dbs = pc_db_access.Policy.query(resource_ref=lv_ac_db.action, enabled=True)
    LOG.debug('Identified %s policies for the action "%s".' % (len(policy_dbs), lv_ac_db.action))

    for policy_db in policy_dbs:
        LOG.debug('Getting driver for policy "%s" (%s).' % (policy_db.ref, policy_db.policy_type))
        driver = engine.get_driver(policy_db.ref, policy_db.policy_type, **policy_db.parameters)

        try:
            message = 'Applying policy "%s" (%s) for liveaction "%s".'
            LOG.info(message % (policy_db.ref, policy_db.policy_type, str(lv_ac_db.id)))
            lv_ac_db = driver.apply_before(lv_ac_db)
        except:
            message = 'An exception occurred while applying policy "%s" (%s) for liveaction "%s".'
            LOG.exception(message % (policy_db.ref, policy_db.policy_type, str(lv_ac_db.id)))

        if lv_ac_db.status == ac_const.LIVEACTION_STATUS_DELAYED:
            break

    return lv_ac_db


def apply_post_run_policies(lv_ac_db):
    LOG.debug('Applying post run policies for liveaction "%s".' % str(lv_ac_db.id))

    policy_dbs = pc_db_access.Policy.query(resource_ref=lv_ac_db.action, enabled=True)
    LOG.debug('Identified %s policies for the action "%s".' % (len(policy_dbs), lv_ac_db.action))

    for policy_db in policy_dbs:
        LOG.debug('Getting driver for policy "%s" (%s).' % (policy_db.ref, policy_db.policy_type))
        driver = engine.get_driver(policy_db.ref, policy_db.policy_type, **policy_db.parameters)

        try:
            message = 'Applying policy "%s" (%s) for liveaction "%s".'
            LOG.info(message % (policy_db.ref, policy_db.policy_type, str(lv_ac_db.id)))
            lv_ac_db = driver.apply_after(lv_ac_db)
        except:
            message = 'An exception occurred while applying policy "%s" (%s) for liveaction "%s".'
            LOG.exception(message % (policy_db.ref, policy_db.policy_type, str(lv_ac_db.id)))

    return lv_ac_db
