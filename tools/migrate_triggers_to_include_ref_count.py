#!/usr/bin/env python

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

from mongoengine.queryset import Q

from st2common import config
from st2common.script_setup import setup as common_setup
from st2common.script_setup import teardown as common_teardown
from st2common.persistence.rule import Rule
from st2common.persistence.trigger import Trigger
from st2common.models.db.trigger import TriggerDB


class TriggerMigrator(object):

    def _get_trigger_with_parameters(self):
        """
        All TriggerDB that has a parameter.
        """
        return TriggerDB.objects(Q(parameters__exists=True) & Q(parameters__nin=[{}]))

    def _get_rules_for_trigger(self, trigger_ref):
        """
        All rules that reference the supplied trigger_ref.
        """
        return Rule.get_all(**{'trigger': trigger_ref})

    def _update_trigger_ref_count(self, trigger_db, ref_count):
        """
        Non-publishing ref_count update to a TriggerDB.
        """
        trigger_db.ref_count = ref_count
        Trigger.add_or_update(trigger_db, publish=False, dispatch_trigger=False)

    def migrate(self):
        """
        Will migrate all Triggers that should have ref_count to have the right ref_count.
        """
        trigger_dbs = self._get_trigger_with_parameters()
        for trigger_db in trigger_dbs:
            trigger_ref = trigger_db.get_reference().ref
            rules = self._get_rules_for_trigger(trigger_ref=trigger_ref)
            ref_count = len(rules)
            print('Updating Trigger %s to ref_count %s' % (trigger_ref, ref_count))
            self._update_trigger_ref_count(trigger_db=trigger_db, ref_count=ref_count)


def setup():
    common_setup(config=config, setup_db=True, register_mq_exchanges=True)


def teartown():
    common_teardown()


def main():
    setup()
    try:
        TriggerMigrator().migrate()
    finally:
        teartown()


if __name__ == '__main__':
    main()
