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

"""
Garbage collection service which deletes old data from the database.
"""

from __future__ import absolute_import

import signal
import datetime
import random

import six
from oslo_config import cfg

from st2common import log as logging
from st2common.util import concurrency
from st2common.constants.exit_codes import SUCCESS_EXIT_CODE
from st2common.constants.exit_codes import FAILURE_EXIT_CODE
from st2common.constants.garbage_collection import DEFAULT_COLLECTION_INTERVAL
from st2common.constants.garbage_collection import DEFAULT_SLEEP_DELAY
from st2common.constants.garbage_collection import MINIMUM_TTL_DAYS
from st2common.constants.garbage_collection import MINIMUM_TTL_DAYS_EXECUTION_OUTPUT
from st2common.util import isotime
from st2common.util.date import get_datetime_utc_now
from st2common.garbage_collection.executions import purge_executions
from st2common.garbage_collection.executions import purge_execution_output_objects
from st2common.garbage_collection.executions import purge_orphaned_workflow_executions
from st2common.garbage_collection.inquiries import purge_inquiries
from st2common.garbage_collection.workflows import (
    purge_workflow_executions,
    purge_task_executions,
)
from st2common.garbage_collection.trigger_instances import purge_trigger_instances
from st2common.garbage_collection.trace import purge_traces
from st2common.garbage_collection.token import purge_tokens
from st2common.garbage_collection.rule_enforcement import purge_rule_enforcements

__all__ = ["GarbageCollectorService"]

LOG = logging.getLogger(__name__)


class GarbageCollectorService(object):
    def __init__(
        self,
        collection_interval=DEFAULT_COLLECTION_INTERVAL,
        sleep_delay=DEFAULT_SLEEP_DELAY,
    ):
        """
        :param collection_interval: How often to check database for old data and perform garbage
               collection.
        :type collection_interval: ``int``

        :param sleep_delay: How long to sleep (in seconds) between collection of different object
                            types.
        :type sleep_delay: ``int``
        """
        self._collection_interval = collection_interval

        self._action_executions_ttl = cfg.CONF.garbagecollector.action_executions_ttl
        self._action_executions_output_ttl = (
            cfg.CONF.garbagecollector.action_executions_output_ttl
        )
        self._trigger_instances_ttl = cfg.CONF.garbagecollector.trigger_instances_ttl
        self._traces_ttl = cfg.CONF.garbagecollector.traces_ttl
        self._tokens_ttl = cfg.CONF.garbagecollector.tokens_ttl
        self._rule_enforcements_ttl = cfg.CONF.garbagecollector.rule_enforcements_ttl
        self._purge_inquiries = cfg.CONF.garbagecollector.purge_inquiries
        self._workflow_execution_max_idle = cfg.CONF.workflow_engine.gc_max_idle_sec
        self._workflow_executions_ttl = (
            cfg.CONF.garbagecollector.workflow_executions_ttl
        )
        self._task_executions_ttl = cfg.CONF.garbagecollector.task_executions_ttl

        self._validate_ttl_values()

        self._sleep_delay = sleep_delay

    def run(self):
        self._running = True

        self._register_signal_handlers()

        # Wait a couple of seconds before performing initial collection to prevent thundering herd
        # effect when restarting multiple services at the same time
        jitter_seconds = random.uniform(0, 3)
        concurrency.sleep(jitter_seconds)

        success_exception_cls = concurrency.get_greenlet_exit_exception_class()

        try:
            self._main_loop()
        except success_exception_cls:
            self._running = False
            return SUCCESS_EXIT_CODE
        except Exception as e:
            LOG.exception("Exception in the garbage collector: %s" % (six.text_type(e)))
            self._running = False
            return FAILURE_EXIT_CODE

        return SUCCESS_EXIT_CODE

    def _register_signal_handlers(self):
        signal.signal(signal.SIGUSR2, self.handle_sigusr2)

    def handle_sigusr2(self, signal_number, stack_frame):
        LOG.info("Forcing garbage collection...")
        self._perform_garbage_collection()

    def shutdown(self):
        self._running = False

    def _main_loop(self):
        while self._running:
            self._perform_garbage_collection()

            LOG.info(
                "Sleeping for %s seconds before next garbage collection..."
                % (self._collection_interval)
            )
            concurrency.sleep(self._collection_interval)

    def _validate_ttl_values(self):
        """
        Validate that a user has supplied reasonable TTL values.
        """
        if (
            self._action_executions_ttl
            and self._action_executions_ttl < MINIMUM_TTL_DAYS
        ):
            raise ValueError(
                "Minimum possible TTL for action_executions_ttl in days is %s"
                % (MINIMUM_TTL_DAYS)
            )

        if (
            self._trigger_instances_ttl
            and self._trigger_instances_ttl < MINIMUM_TTL_DAYS
        ):
            raise ValueError(
                "Minimum possible TTL for trigger_instances_ttl in days is %s"
                % (MINIMUM_TTL_DAYS)
            )

        if (
            self._action_executions_output_ttl
            and self._action_executions_output_ttl < MINIMUM_TTL_DAYS_EXECUTION_OUTPUT
        ):
            raise ValueError(
                (
                    "Minimum possible TTL for action_executions_output_ttl in days "
                    "is %s"
                )
                % (MINIMUM_TTL_DAYS_EXECUTION_OUTPUT)
            )
        if self._traces_ttl and self._traces_ttl < MINIMUM_TTL_DAYS:
            raise ValueError(
                "Minimum possible TTL for traces_ttl in days is %s" % (MINIMUM_TTL_DAYS)
            )

        if self._tokens_ttl and self._tokens_ttl < MINIMUM_TTL_DAYS:
            raise ValueError(
                "Minimum possible TTL for tokens_ttl in days is %s" % (MINIMUM_TTL_DAYS)
            )

        if (
            self._rule_enforcements_ttl
            and self._rule_enforcements_ttl < MINIMUM_TTL_DAYS
        ):
            raise ValueError(
                "Minimum possible TTL for rule_enforcements_ttl in days is %s"
                % (MINIMUM_TTL_DAYS)
            )

    def _perform_garbage_collection(self):
        LOG.info("Performing garbage collection...")

        proc_message = "Performing garbage collection for %s."
        skip_message = "Skipping garbage collection for %s since it's not configured."

        # Note: We sleep for a bit between garbage collection of each object type to prevent busy
        # waiting
        obj_type = "action executions"

        if (
            self._action_executions_ttl
            and self._action_executions_ttl >= MINIMUM_TTL_DAYS
        ):
            LOG.info(proc_message, obj_type)
            self._purge_action_executions()
            concurrency.sleep(self._sleep_delay)
        else:
            LOG.debug(skip_message, obj_type)

        obj_type = "action executions output"

        if (
            self._action_executions_output_ttl
            and self._action_executions_output_ttl >= MINIMUM_TTL_DAYS_EXECUTION_OUTPUT
        ):
            LOG.info(proc_message, obj_type)
            self._purge_action_executions_output()
            concurrency.sleep(self._sleep_delay)
        else:
            LOG.debug(skip_message, obj_type)

        obj_type = "trigger instances"

        if (
            self._trigger_instances_ttl
            and self._trigger_instances_ttl >= MINIMUM_TTL_DAYS
        ):
            LOG.info(proc_message, obj_type)
            self._purge_trigger_instances()
            concurrency.sleep(self._sleep_delay)
        else:
            LOG.debug(skip_message, obj_type)

        obj_type = "trace"

        if self._traces_ttl and self._traces_ttl >= MINIMUM_TTL_DAYS:
            LOG.info(proc_message, obj_type)
            self._purge_traces()
            concurrency.sleep(self._sleep_delay)
        else:
            LOG.debug(skip_message, obj_type)

        obj_type = "token"

        if self._tokens_ttl and self._tokens_ttl >= MINIMUM_TTL_DAYS:

            LOG.info(proc_message, obj_type)
            self._purge_tokens()
            concurrency.sleep(self._sleep_delay)
        else:
            LOG.debug(skip_message, obj_type)

        obj_type = "rule enforcement"

        if (
            self._rule_enforcements_ttl
            and self._rule_enforcements_ttl >= MINIMUM_TTL_DAYS
        ):
            LOG.info(proc_message, obj_type)
            self._purge_rule_enforcements()
            concurrency.sleep(self._sleep_delay)
        else:
            LOG.debug(skip_message, obj_type)

        obj_type = "inquiries"
        if self._purge_inquiries:
            LOG.info(proc_message, obj_type)
            self._timeout_inquiries()
            concurrency.sleep(self._sleep_delay)
        else:
            LOG.debug(skip_message, obj_type)

        obj_type = "orphaned workflow executions"
        if self._workflow_execution_max_idle > 0:
            LOG.info(proc_message, obj_type)
            self._purge_orphaned_workflow_executions()
            concurrency.sleep(self._sleep_delay)
        else:
            LOG.debug(skip_message, obj_type)

        obj_type = "workflow task executions"
        if self._task_executions_ttl and self._task_executions_ttl >= MINIMUM_TTL_DAYS:
            LOG.info(proc_message, obj_type)
            self._purge_task_executions()
            concurrency.sleep(self._sleep_delay)
        else:
            LOG.debug(skip_message, obj_type)

        obj_type = "workflow executions"
        if (
            self._workflow_executions_ttl
            and self._workflow_executions_ttl >= MINIMUM_TTL_DAYS
        ):
            LOG.info(proc_message, obj_type)
            self._purge_workflow_executions()
            concurrency.sleep(self._sleep_delay)
        else:
            LOG.debug(skip_message, obj_type)

    def _purge_action_executions(self):
        """
        Purge action executions and corresponding live action, stdout and stderr object which match
        the criteria defined in the config.
        """
        utc_now = get_datetime_utc_now()
        timestamp = utc_now - datetime.timedelta(days=self._action_executions_ttl)

        # Another sanity check to make sure we don't delete new executions
        if timestamp > (utc_now - datetime.timedelta(days=MINIMUM_TTL_DAYS)):
            raise ValueError(
                "Calculated timestamp would violate the minimum TTL constraint"
            )

        timestamp_str = isotime.format(dt=timestamp)
        LOG.info("Deleting action executions older than: %s" % (timestamp_str))

        if timestamp >= utc_now:
            raise ValueError(
                f"Calculated timestamp ({timestamp}) is"
                f" later than now in UTC ({utc_now})."
            )

        try:
            purge_executions(logger=LOG, timestamp=timestamp)
        except Exception as e:
            LOG.exception("Failed to delete executions: %s" % (six.text_type(e)))

        return True

    def _purge_workflow_executions(self):
        """
        Purge workflow executions and corresponding live action, stdout and stderr
        object which match the criteria defined in the config.
        """
        utc_now = get_datetime_utc_now()
        timestamp = utc_now - datetime.timedelta(days=self._workflow_executions_ttl)

        # Another sanity check to make sure we don't delete new executions
        if timestamp > (utc_now - datetime.timedelta(days=MINIMUM_TTL_DAYS)):
            raise ValueError(
                "Calculated timestamp would violate the minimum TTL constraint"
            )

        timestamp_str = isotime.format(dt=timestamp)
        LOG.info("Deleting workflow executions older than: %s" % (timestamp_str))

        assert timestamp < utc_now

        try:
            purge_workflow_executions(logger=LOG, timestamp=timestamp)
        except Exception as e:
            LOG.exception(
                "Failed to delete workflow executions: %s" % (six.text_type(e))
            )

        return True

    def _purge_task_executions(self):
        """
        Purge workflow task executions and corresponding live action, stdout and stderr
        object which match the criteria defined in the config.
        """
        utc_now = get_datetime_utc_now()
        timestamp = utc_now - datetime.timedelta(days=self._task_executions_ttl)

        # Another sanity check to make sure we don't delete new executions
        if timestamp > (utc_now - datetime.timedelta(days=MINIMUM_TTL_DAYS)):
            raise ValueError(
                "Calculated timestamp would violate the minimum TTL constraint"
            )

        timestamp_str = isotime.format(dt=timestamp)
        LOG.info("Deleting workflow task executions older than: %s" % (timestamp_str))

        assert timestamp < utc_now

        try:
            purge_task_executions(logger=LOG, timestamp=timestamp)
        except Exception as e:
            LOG.exception(
                "Failed to delete workflow task executions: %s" % (six.text_type(e))
            )

        return True

    def _purge_action_executions_output(self):
        utc_now = get_datetime_utc_now()
        timestamp = utc_now - datetime.timedelta(
            days=self._action_executions_output_ttl
        )

        # Another sanity check to make sure we don't delete new objects
        if timestamp > (
            utc_now - datetime.timedelta(days=MINIMUM_TTL_DAYS_EXECUTION_OUTPUT)
        ):
            raise ValueError(
                "Calculated timestamp would violate the minimum TTL constraint"
            )

        timestamp_str = isotime.format(dt=timestamp)
        LOG.info(
            "Deleting action executions output objects older than: %s" % (timestamp_str)
        )

        if timestamp >= utc_now:
            raise ValueError(
                f"Calculated timestamp ({timestamp}) is"
                f" later than now in UTC ({utc_now})."
            )

        try:
            purge_execution_output_objects(logger=LOG, timestamp=timestamp)
        except Exception as e:
            LOG.exception(
                "Failed to delete execution output objects: %s" % (six.text_type(e))
            )

        return True

    def _purge_trigger_instances(self):
        """
        Purge trigger instances which match the criteria defined in the config.
        """
        utc_now = get_datetime_utc_now()
        timestamp = utc_now - datetime.timedelta(days=self._trigger_instances_ttl)

        # Another sanity check to make sure we don't delete new executions
        if timestamp > (utc_now - datetime.timedelta(days=MINIMUM_TTL_DAYS)):
            raise ValueError(
                "Calculated timestamp would violate the minimum TTL constraint"
            )

        timestamp_str = isotime.format(dt=timestamp)
        LOG.info("Deleting trigger instances older than: %s" % (timestamp_str))

        if timestamp >= utc_now:
            raise ValueError(
                f"Calculated timestamp ({timestamp}) is"
                f" later than now in UTC ({utc_now})."
            )

        try:
            purge_trigger_instances(logger=LOG, timestamp=timestamp)
        except Exception as e:
            LOG.exception("Failed to trigger instances: %s" % (six.text_type(e)))

        return True

    def _purge_traces(self):
        """
        Purge trace objects which match the criteria defined in the config.
        """
        utc_now = get_datetime_utc_now()
        timestamp = utc_now - datetime.timedelta(days=self._traces_ttl)

        # Another sanity check to make sure we don't delete new objects
        if timestamp > (utc_now - datetime.timedelta(days=MINIMUM_TTL_DAYS)):
            raise ValueError(
                "Calculated timestamp would violate the minimum TTL constraint"
            )

        timestamp_str = isotime.format(dt=timestamp)
        LOG.info("Deleting trace objects older than: %s" % (timestamp_str))

        if timestamp >= utc_now:
            raise ValueError(
                f"Calculated timestamp ({timestamp}) is"
                f" later than now in UTC ({utc_now})."
            )

        try:
            purge_traces(logger=LOG, timestamp=timestamp)
        except Exception as e:
            LOG.exception("Failed to delete trace: %s" % (six.text_type(e)))

        return True

    def _purge_tokens(self):
        """
        Purge token objects which match the criteria defined in the config.
        """
        utc_now = get_datetime_utc_now()
        timestamp = utc_now - datetime.timedelta(days=self._tokens_ttl)

        # Another sanity check to make sure we don't delete new objects
        if timestamp > (utc_now - datetime.timedelta(days=MINIMUM_TTL_DAYS)):
            raise ValueError(
                "Calculated timestamp would violate the minimum TTL constraint"
            )

        timestamp_str = isotime.format(dt=timestamp)
        LOG.info("Deleting token objects expired older than: %s" % (timestamp_str))

        if timestamp >= utc_now:
            raise ValueError(
                f"Calculated timestamp ({timestamp}) is"
                f" later than now in UTC ({utc_now})."
            )

        try:
            purge_tokens(logger=LOG, timestamp=timestamp)
        except Exception as e:
            LOG.exception("Failed to delete token: %s" % (six.text_type(e)))

        return True

    def _purge_rule_enforcements(self):
        """
        Purge rule enforcements which match the criteria defined in the config.
        """
        utc_now = get_datetime_utc_now()
        timestamp = utc_now - datetime.timedelta(days=self._rule_enforcements_ttl)

        # Another sanity check to make sure we don't delete new objects
        if timestamp > (utc_now - datetime.timedelta(days=MINIMUM_TTL_DAYS)):
            raise ValueError(
                "Calculated timestamp would violate the minimum TTL constraint"
            )

        timestamp_str = isotime.format(dt=timestamp)
        LOG.info("Deleting rule enforcements older than: %s" % (timestamp_str))

        if timestamp >= utc_now:
            raise ValueError(
                f"Calculated timestamp ({timestamp}) is"
                f" later than now in UTC ({utc_now})."
            )

        try:
            purge_rule_enforcements(logger=LOG, timestamp=timestamp)
        except Exception as e:
            LOG.exception("Failed to delete rule enforcements: %s" % (six.text_type(e)))

        return True

    def _timeout_inquiries(self):
        """Mark Inquiries as "timeout" that have exceeded their TTL"""
        try:
            purge_inquiries(logger=LOG)
        except Exception as e:
            LOG.exception("Failed to purge inquiries: %s" % (six.text_type(e)))

        return True

    def _purge_orphaned_workflow_executions(self):
        """
        Purge workflow executions that are idled and orphaned.
        """
        try:
            purge_orphaned_workflow_executions(logger=LOG)
        except Exception as e:
            LOG.exception(
                "Failed to purge orphaned workflow executions: %s" % (six.text_type(e))
            )

        return True
