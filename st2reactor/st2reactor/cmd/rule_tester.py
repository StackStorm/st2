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
import sys

from oslo_config import cfg

from st2common import config
from st2common import log as logging
from st2common.config import do_register_cli_opts
from st2common.service_setup import db_setup
from st2common.script_setup import setup as common_setup
from st2common.script_setup import teardown as common_teardown
from st2reactor.rules.tester import RuleTester

__all__ = ["main"]

LOG = logging.getLogger(__name__)


def _register_cli_opts():
    cli_opts = [
        cfg.StrOpt(
            "rule", default=None, help="Path to the file containing rule definition."
        ),
        cfg.StrOpt("rule-ref", default=None, help="Ref of the rule."),
        cfg.StrOpt(
            "trigger-instance",
            default=None,
            help="Path to the file containing trigger instance definition",
        ),
        cfg.StrOpt(
            "trigger-instance-id",
            default=None,
            help="Id of the Trigger Instance to use for validation.",
        ),
        cfg.BoolOpt(
            "offline",
            default=False,
            help="Run st2-rule-tester without DB connection - can only be used in connection with 'rule' and 'trigger-instance' options",
        ),
    ]
    do_register_cli_opts(cli_opts)


def main():
    _register_cli_opts()

    common_setup(config=config, setup_db=False, register_mq_exchanges=False)

    # Setup DB if not running offline
    if not cfg.CONF.offline:
        db_setup()
    # If running offline check that neither rule_ref or trigger_instance_id are provided as they require the DB.
    elif cfg.CONF.rule_ref or cfg.CONF.trigger_instance_id:
        LOG.critical(
            "'rule-ref' and/or 'trigger-instance-id' cannot be used in 'offline' mode"
        )
        sys.exit(2)

    try:
        tester = RuleTester(
            rule_file_path=cfg.CONF.rule,
            rule_ref=cfg.CONF.rule_ref,
            trigger_instance_file_path=cfg.CONF.trigger_instance,
            trigger_instance_id=cfg.CONF.trigger_instance_id,
        )
        matches = tester.evaluate()
    finally:
        common_teardown()

    if matches:
        LOG.info("=== RULE MATCHES ===")
        sys.exit(0)
    else:
        LOG.info("=== RULE DOES NOT MATCH ===")
        sys.exit(1)
