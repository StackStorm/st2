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
from oslo_config import cfg

from st2common.constants import action as action_constants
from st2common.models.db.auth import UserDB
from st2common.persistence.execution import ActionExecution
from st2common.services import action as action_service
from st2common.services import executions
from st2common.runners.utils import invoke_post_run
from st2common.util import action_db as action_utils
from st2common.util.action_db import get_action_by_ref
from st2common.util.date import get_datetime_utc_now

__all__ = [
    "purge_inquiries",
]


def purge_inquiries(logger):
    """Purge Inquiries that have exceeded their configured TTL

    At the moment, Inquiries do not have their own database model, so this function effectively
    is another, more specialized GC for executions. It will look for executions with a 'pending'
    status that use the 'inquirer' runner, which is the current definition for an Inquiry.

    Then it will mark those that have a nonzero TTL have existed longer than their TTL as
    "timed out". It will then request that the parent workflow(s) resume, where the failure
    can be handled as the user desires.
    """

    # Get all existing Inquiries
    filters = {
        "runner__name": "inquirer",
        "status": action_constants.LIVEACTION_STATUS_PENDING,
    }
    inquiries = list(ActionExecution.query(**filters))

    gc_count = 0

    # Inspect each Inquiry, and determine if TTL is expired
    for inquiry in inquiries:

        ttl = int(inquiry.result.get("ttl"))
        if ttl <= 0:
            logger.debug("Inquiry %s has a TTL of %s. Skipping." % (inquiry.id, ttl))
            continue

        min_since_creation = int(
            (get_datetime_utc_now() - inquiry.start_timestamp).total_seconds() / 60
        )

        logger.debug(
            "Inquiry %s has a TTL of %s and was started %s minute(s) ago"
            % (inquiry.id, ttl, min_since_creation)
        )

        if min_since_creation > ttl:
            gc_count += 1
            logger.info(
                "TTL expired for Inquiry %s. Marking as timed out." % inquiry.id
            )

            liveaction_db = action_utils.update_liveaction_status(
                status=action_constants.LIVEACTION_STATUS_TIMED_OUT,
                result=inquiry.result,
                liveaction_id=inquiry.liveaction.get("id"),
            )
            executions.update_execution(liveaction_db)

            # Call Inquiry runner's post_run to trigger callback to workflow
            action_db = get_action_by_ref(liveaction_db.action)
            invoke_post_run(liveaction_db=liveaction_db, action_db=action_db)

            if liveaction_db.context.get("parent"):
                # Request that root workflow resumes
                root_liveaction = action_service.get_root_liveaction(liveaction_db)
                action_service.request_resume(
                    root_liveaction, UserDB(name=cfg.CONF.system_user.user)
                )

    logger.info('Marked %s ttl-expired Inquiries as "timed out".' % (gc_count))
