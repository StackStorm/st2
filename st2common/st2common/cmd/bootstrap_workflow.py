# Copyright 2020 The StackStorm Authors.
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


"""
Manually bootstrap-resume a single workflow execution that was paused by a
prior workflow engine shutdown. Bypasses coordination first-member election
and the automatic-bootstrap lookback window; the operator is asserting they
want this specific execution resumed now.
"""

from __future__ import absolute_import

from oslo_config import cfg

from st2common import config
from st2common import log as logging
from st2common.config import do_register_cli_opts
from st2common.constants import action as ac_const
from st2common.constants.exit_codes import FAILURE_EXIT_CODE
from st2common.constants.exit_codes import SUCCESS_EXIT_CODE
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.script_setup import setup as common_setup
from st2common.script_setup import teardown as common_teardown
from st2common.services import workflows as wf_svc


__all__ = ["main"]

LOG = logging.getLogger(__name__)


def _register_cli_opts():
    cli_opts = [
        cfg.StrOpt(
            "execution-id",
            default=None,
            help="ActionExecution id of the shutdown-paused workflow to resume.",
        ),
    ]
    do_register_cli_opts(cli_opts)


def _bootstrap_one(execution_id):
    ac_ex_db = ex_db_access.ActionExecution.get_by_id(execution_id)
    lv_ac_db = lv_db_access.LiveAction.get_by_id(str(ac_ex_db.liveaction_id))

    if lv_ac_db.status != ac_const.LIVEACTION_STATUS_PAUSED:
        LOG.error(
            "Execution %s is in status %r, not %r. Refusing to bootstrap-resume.",
            execution_id,
            lv_ac_db.status,
            ac_const.LIVEACTION_STATUS_PAUSED,
        )
        return FAILURE_EXIT_CODE

    paused_by = lv_ac_db.context.get("paused_by")
    if paused_by != wf_svc.WORKFLOW_ENGINE_START_STOP_SEQ:
        LOG.error(
            "Execution %s was not paused by an engine shutdown "
            "(paused_by=%r). Use `st2 execution resume` for user-paused workflows.",
            execution_id,
            paused_by,
        )
        return FAILURE_EXIT_CODE

    wf_svc.bootstrap_resume_execution(lv_ac_db)
    LOG.info("Bootstrap-resumed execution %s.", execution_id)
    return SUCCESS_EXIT_CODE


def main():
    _register_cli_opts()
    common_setup(config=config, setup_db=True, register_mq_exchanges=True)

    execution_id = cfg.CONF.execution_id
    if not execution_id:
        LOG.error("--execution-id is required. Aborting.")
        common_teardown()
        return FAILURE_EXIT_CODE

    try:
        return _bootstrap_one(execution_id)
    except Exception as e:
        LOG.exception("Failed to bootstrap-resume execution %s: %s", execution_id, e)
        return FAILURE_EXIT_CODE
    finally:
        common_teardown()
