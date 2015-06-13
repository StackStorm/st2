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


"""

Tags: Load test, stress test.

A utility script that injects trigger instances into st2 system.

This tool is designed with stress/load testing in mind. Trigger
instances need appropriate rules to be setup so there is some
meaningful work.

"""

import os
import random
import sys

import eventlet
from oslo.config import cfg
import yaml

from st2common import config
from st2common.util import isotime
from st2common.transport.reactor import TriggerDispatcher


def do_register_cli_opts(opts, ignore_errors=False):
    for opt in opts:
        try:
            cfg.CONF.register_cli_opt(opt)
        except:
            if not ignore_errors:
                raise


def _monkey_patch():
    eventlet.monkey_patch(
        os=True,
        select=True,
        socket=True,
        thread=False if '--use-debugger' in sys.argv else True,
        time=True)


def _inject_instances(trigger, rate_per_trigger, duration, payload={}):
    start = isotime.get_datetime_utc_now()
    elapsed = 0.0
    count = 0

    dispatcher = TriggerDispatcher()
    while elapsed < duration:
        # print('Dispatching trigger %s at time %s', trigger, isotime.get_datetime_utc_now())
        dispatcher.dispatch(trigger, payload)
        delta = random.expovariate(rate_per_trigger)
        eventlet.sleep(delta)
        elapsed = (isotime.get_datetime_utc_now() - start).seconds/60.0
        count += 1

    print('%s: Emitted %d triggers in %d seconds' % (trigger, count, elapsed))


def main():
    _monkey_patch()

    cli_opts = [
        cfg.IntOpt('rate', default=100,
                   help='Rate of trigger injection measured in instances in per sec.' +
                   ' Assumes a default exponential distribution in time so arrival is poisson.'),
        cfg.ListOpt('triggers', required=False,
                    help='List of triggers for which instances should be fired.' +
                    ' Uniform distribution will be followed if there is more than one' +
                    'trigger.'),
        cfg.StrOpt('schema_file', default=None,
                   help='Path to schema file defining trigger and payload.'),
        cfg.IntOpt('duration', default=1,
                   help='Duration of stress test in minutes.')
    ]
    do_register_cli_opts(cli_opts)
    config.parse_args()

    # Get config values
    triggers = cfg.CONF.triggers
    trigger_payload_schema = {}

    if not triggers:
        if (cfg.CONF.schema_file is None or cfg.CONF.schema_file == '' or
                not os.path.exists(cfg.CONF.schema_file)):
            print('Either "triggers" need to be provided or a schema file containing' +
                  ' triggers should be provided.')
            return
        with open(cfg.CONF.schema_file) as fd:
            trigger_payload_schema = yaml.safe_load(fd)
            triggers = trigger_payload_schema.keys()
            print('Triggers=%s' % triggers)

    rate = cfg.CONF.rate
    rate_per_trigger = int(rate/len(triggers))
    duration = cfg.CONF.duration

    dispatcher_pool = eventlet.GreenPool(len(triggers))

    for trigger in triggers:
        payload = trigger_payload_schema.get(trigger, {})
        dispatcher_pool.spawn(_inject_instances, trigger, rate_per_trigger, duration,
                              payload=payload)
        eventlet.sleep(random.uniform(0, 1))
    dispatcher_pool.waitall()


if __name__ == '__main__':
    main()
