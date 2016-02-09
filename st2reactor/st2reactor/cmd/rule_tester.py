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

import sys

from oslo_config import cfg

from st2common import config
from st2common import log as logging
from st2common.script_setup import setup as common_setup
from st2common.script_setup import teardown as common_teardown
from st2reactor.rules.tester import RuleTester

__all__ = [
    'main'
]

LOG = logging.getLogger(__name__)


def _do_register_cli_opts(opts, ignore_errors=False):
    for opt in opts:
        try:
            cfg.CONF.register_cli_opt(opt)
        except:
            if not ignore_errors:
                raise


def _register_cli_opts():
    cli_opts = [
        cfg.StrOpt('rule', default=None,
                   help='Path to the file containing rule definition.'),
        cfg.StrOpt('rule-ref', default=None,
                   help='Ref of the rule.'),
        cfg.StrOpt('trigger-instance', default=None,
                   help='Path to the file containing trigger instance definition'),
        cfg.StrOpt('trigger-instance-id', default=None,
                   help='Id of the Trigger Instance to use for validation.')
    ]
    _do_register_cli_opts(cli_opts)


def main():
    _register_cli_opts()
    common_setup(config=config, setup_db=True, register_mq_exchanges=False)

    try:
        tester = RuleTester(rule_file_path=cfg.CONF.rule,
                            rule_ref=cfg.CONF.rule_ref,
                            trigger_instance_file_path=cfg.CONF.trigger_instance,
                            trigger_instance_id=cfg.CONF.trigger_instance_id)
        matches = tester.evaluate()
    finally:
        common_teardown()

    if matches:
        LOG.info('=== RULE MATCHES ===')
        sys.exit(0)
    else:
        LOG.info('=== RULE DOES NOT MATCH ===')
        sys.exit(1)
