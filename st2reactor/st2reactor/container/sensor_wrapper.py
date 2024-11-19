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

# Note: We need to perform monkey patching in the worker. If we do it in
# the master process (gunicorn_config.py), it breaks tons of things
# including shutdown
# NOTE: It's important that we perform monkey patch as early as possible before any other modules
# are imported, otherwise SSL support for sensor clients won't work.
# See https://github.com/StackStorm/st2/issues/4832, https://github.com/StackStorm/st2/issues/4975
# and https://github.com/gevent/gevent/issues/1016
# for details.

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import os
import json
import atexit
import argparse
import traceback

import six
from oslo_config import cfg

from st2common import log as logging
from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.logging.misc import set_log_level_for_all_loggers
from st2common.models.api.trigger import TriggerAPI
from st2common.persistence.db_init import db_setup_with_retry
from st2common.util import loader
from st2common.util.config_loader import ContentPackConfigLoader
from st2common.services.triggerwatcher import TriggerWatcher
from st2common.services.trigger_dispatcher import TriggerDispatcherService
from st2reactor.sensor.base import Sensor
from st2reactor.sensor.base import PollingSensor
from st2reactor.sensor import config
from st2common.services.datastore import SensorDatastoreService
from st2common.util.monkey_patch import use_select_poll_workaround


LOG = logging.getLogger(__name__)

__all__ = ["SensorWrapper", "SensorService"]

use_select_poll_workaround(nose_only=False)


class SensorService(object):
    """
    Instance of this class is passed to the sensor instance and exposes "public"
    methods which can be called by the sensor.
    """

    def __init__(self, sensor_wrapper):
        self._sensor_wrapper = sensor_wrapper
        self._logger = self._sensor_wrapper._logger

        self._trigger_dispatcher_service = TriggerDispatcherService(
            logger=sensor_wrapper._logger
        )
        self._datastore_service = SensorDatastoreService(
            logger=self._logger,
            pack_name=self._sensor_wrapper._pack,
            class_name=self._sensor_wrapper._class_name,
            api_username="sensor_service",
        )

        self._client = None

    @property
    def datastore_service(self):
        return self._datastore_service

    def get_logger(self, name):
        """
        Retrieve an instance of a logger to be used by the sensor class.
        """
        logger_name = "%s.%s" % (self._sensor_wrapper._logger.name, name)
        logger = logging.getLogger(logger_name)
        logger.propagate = True

        return logger

    ##################################
    # General methods
    ##################################

    def get_user_info(self):
        return self._datastore_service.get_user_info()

    ##################################
    # Sensor related methods
    ##################################

    def dispatch(self, trigger, payload=None, trace_tag=None):
        # Provided by the parent BaseTriggerDispatcherService class
        return self._trigger_dispatcher_service.dispatch(
            trigger=trigger,
            payload=payload,
            trace_tag=trace_tag,
            throw_on_validation_error=False,
        )

    def dispatch_with_context(self, trigger, payload=None, trace_context=None):
        """
        Method which dispatches the trigger.

        :param trigger: Full name / reference of the trigger.
        :type trigger: ``str``

        :param payload: Trigger payload.
        :type payload: ``dict``

        :param trace_context: Trace context to associate with Trigger.
        :type trace_context: ``st2common.api.models.api.trace.TraceContext``
        """
        # Provided by the parent BaseTriggerDispatcherService class
        return self._trigger_dispatcher_service.dispatch_with_context(
            trigger=trigger,
            payload=payload,
            trace_context=trace_context,
            throw_on_validation_error=False,
        )

    ##################################
    # Methods for datastore management
    ##################################

    def list_values(self, local=True, prefix=None, limit=None, offset=None):
        return self.datastore_service.list_values(
            local=local, prefix=prefix, limit=limit, offset=offset
        )

    def get_value(self, name, local=True, scope=SYSTEM_SCOPE, decrypt=False):
        return self.datastore_service.get_value(
            name=name, local=local, scope=scope, decrypt=decrypt
        )

    def set_value(
        self, name, value, ttl=None, local=True, scope=SYSTEM_SCOPE, encrypt=False
    ):
        return self.datastore_service.set_value(
            name=name, value=value, ttl=ttl, local=local, scope=scope, encrypt=encrypt
        )

    def delete_value(self, name, local=True, scope=SYSTEM_SCOPE):
        return self.datastore_service.delete_value(name=name, local=local, scope=scope)


class SensorWrapper(object):
    def __init__(
        self,
        pack,
        file_path,
        class_name,
        trigger_types,
        poll_interval=None,
        parent_args=None,
        db_ensure_indexes=True,
    ):
        """
        :param pack: Name of the pack this sensor belongs to.
        :type pack: ``str``

        :param file_path: Path to the sensor module file.
        :type file_path: ``str``

        :param class_name: Sensor class name.
        :type class_name: ``str``

        :param trigger_types: A list of references to trigger types which
                                  belong to this sensor.
        :type trigger_types: ``list`` of ``str``

        :param poll_interval: Sensor poll interval (in seconds).
        :type poll_interval: ``int`` or ``None``

        :param parent_args: Command line arguments passed to the parent process.
        :type parse_args: ``list``

        :param db_ensure_indexes: True to ensure indexes. This should really only be set to False
                                  in tests to speed things up.
        """
        self._pack = pack
        self._file_path = file_path
        self._class_name = class_name
        self._trigger_types = trigger_types or []
        self._poll_interval = poll_interval
        self._parent_args = parent_args or []
        self._trigger_names = {}

        # 1. Parse the config with inherited parent args
        try:
            config.parse_args(args=self._parent_args)
        except Exception:
            LOG.exception(
                "Failed to parse config using parent args "
                '(parent_args=%s): "%s".' % (str(self._parent_args))
            )

        # 2. Establish DB connection
        username = (
            cfg.CONF.database.username
            if hasattr(cfg.CONF.database, "username")
            else None
        )
        password = (
            cfg.CONF.database.password
            if hasattr(cfg.CONF.database, "password")
            else None
        )
        db_setup_with_retry(
            cfg.CONF.database.db_name,
            cfg.CONF.database.host,
            cfg.CONF.database.port,
            username=username,
            password=password,
            ensure_indexes=db_ensure_indexes,
            tls=cfg.CONF.database.tls,
            tls_certificate_key_file=cfg.CONF.database.tls_certificate_key_file,
            tls_certificate_key_file_password=cfg.CONF.database.tls_certificate_key_file_password,
            tls_allow_invalid_certificates=cfg.CONF.database.tls_allow_invalid_certificates,
            tls_ca_file=cfg.CONF.database.tls_ca_file,
            ssl_cert_reqs=cfg.CONF.database.ssl_cert_reqs,  # deprecated
            authentication_mechanism=cfg.CONF.database.authentication_mechanism,
            ssl_match_hostname=cfg.CONF.database.ssl_match_hostname,
        )

        # 3. Instantiate the watcher
        self._trigger_watcher = TriggerWatcher(
            create_handler=self._handle_create_trigger,
            update_handler=self._handle_update_trigger,
            delete_handler=self._handle_delete_trigger,
            trigger_types=self._trigger_types,
            queue_suffix="sensorwrapper_%s_%s" % (self._pack, self._class_name),
            exclusive=True,
        )

        # 4. Set up logging
        self._logger = logging.getLogger(
            "SensorWrapper.%s.%s" % (self._pack, self._class_name)
        )
        logging.setup(cfg.CONF.sensorcontainer.logging)

        if "--debug" in parent_args:
            set_log_level_for_all_loggers()
        else:
            # NOTE: statsd logger logs everything by default under INFO so we ignore those log
            # messages unless verbose / debug mode is used
            logging.ignore_statsd_log_messages()

        self._sensor_instance = self._get_sensor_instance()

    def run(self):
        atexit.register(self.stop)

        self._trigger_watcher.start()
        self._logger.info("Watcher started")

        self._logger.info("Running sensor initialization code")
        self._sensor_instance.setup()

        if self._poll_interval:
            message = "Running sensor in active mode (poll interval=%ss)" % (
                self._poll_interval
            )
        else:
            message = "Running sensor in passive mode"

        self._logger.info(message)

        try:
            self._sensor_instance.run()
        except Exception as e:
            # Include traceback
            msg = 'Sensor "%s" run method raised an exception: %s.' % (
                self._class_name,
                six.text_type(e),
            )
            self._logger.warning(msg, exc_info=True)
            raise Exception(msg)

    def stop(self):
        # Stop watcher
        self._logger.info("Stopping trigger watcher")
        self._trigger_watcher.stop()

        # Run sensor cleanup code
        self._logger.info("Invoking cleanup on sensor")
        self._sensor_instance.cleanup()

    ##############################################
    # Event handler methods for the trigger events
    ##############################################

    def _handle_create_trigger(self, trigger):
        self._logger.debug(
            'Calling sensor "add_trigger" method (trigger.type=%s)' % (trigger.type)
        )
        self._trigger_names[str(trigger.id)] = trigger

        trigger = self._sanitize_trigger(trigger=trigger)
        self._sensor_instance.add_trigger(trigger=trigger)

    def _handle_update_trigger(self, trigger):
        self._logger.debug(
            'Calling sensor "update_trigger" method (trigger.type=%s)' % (trigger.type)
        )
        self._trigger_names[str(trigger.id)] = trigger

        trigger = self._sanitize_trigger(trigger=trigger)
        self._sensor_instance.update_trigger(trigger=trigger)

    def _handle_delete_trigger(self, trigger):
        trigger_id = str(trigger.id)
        if trigger_id not in self._trigger_names:
            return

        self._logger.debug(
            'Calling sensor "remove_trigger" method (trigger.type=%s)' % (trigger.type)
        )
        del self._trigger_names[trigger_id]

        trigger = self._sanitize_trigger(trigger=trigger)
        self._sensor_instance.remove_trigger(trigger=trigger)

    def _get_sensor_instance(self):
        """
        Retrieve instance of a sensor class.
        """
        _, filename = os.path.split(self._file_path)
        module_name, _ = os.path.splitext(filename)

        try:
            sensor_class = loader.register_plugin_class(
                base_class=Sensor,
                file_path=self._file_path,
                class_name=self._class_name,
            )
        except Exception as e:
            tb_msg = traceback.format_exc()
            msg = (
                'Failed to load sensor class from file "%s" (sensor file most likely doesn\'t '
                "exist or contains invalid syntax): %s"
                % (self._file_path, six.text_type(e))
            )
            msg += "\n\n" + tb_msg
            exc_cls = type(e)
            raise exc_cls(msg)

        if not sensor_class:
            raise ValueError(
                'Sensor module is missing a class with name "%s"' % (self._class_name)
            )

        sensor_class_kwargs = {}
        sensor_class_kwargs["sensor_service"] = SensorService(sensor_wrapper=self)

        sensor_config = self._get_sensor_config()
        sensor_class_kwargs["config"] = sensor_config

        if self._poll_interval and issubclass(sensor_class, PollingSensor):
            sensor_class_kwargs["poll_interval"] = self._poll_interval

        try:
            sensor_instance = sensor_class(**sensor_class_kwargs)
        except Exception:
            self._logger.exception(
                'Failed to instantiate "%s" sensor class' % (self._class_name)
            )
            raise Exception(
                'Failed to instantiate "%s" sensor class' % (self._class_name)
            )

        return sensor_instance

    def _get_sensor_config(self):
        config_loader = ContentPackConfigLoader(pack_name=self._pack)
        config = config_loader.get_config()

        if config:
            self._logger.info('Found config for sensor "%s"' % (self._class_name))
        else:
            self._logger.info('No config found for sensor "%s"' % (self._class_name))

        return config

    def _sanitize_trigger(self, trigger):
        sanitized = TriggerAPI.from_model(trigger).to_dict()
        return sanitized


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sensor runner wrapper")
    parser.add_argument(
        "--pack", required=True, help="Name of the pack this sensor belongs to"
    )
    parser.add_argument("--file-path", required=True, help="Path to the sensor module")
    parser.add_argument("--class-name", required=True, help="Name of the sensor class")
    parser.add_argument(
        "--trigger-type-refs",
        required=False,
        help="Comma delimited string of trigger type references",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=None,
        required=False,
        help="Sensor poll interval",
    )
    parser.add_argument(
        "--parent-args",
        required=False,
        help="Command line arguments passed to the parent process",
    )
    args = parser.parse_args()

    trigger_types = args.trigger_type_refs
    trigger_types = trigger_types.split(",") if trigger_types else []
    parent_args = json.loads(args.parent_args) if args.parent_args else []

    if not isinstance(parent_args, list):
        raise TypeError(
            "Command line arguments passed to the parent process must be a list"
            f" (was {type(parent_args)})."
        )

    obj = SensorWrapper(
        pack=args.pack,
        file_path=args.file_path,
        class_name=args.class_name,
        trigger_types=trigger_types,
        poll_interval=args.poll_interval,
        parent_args=parent_args,
    )
    obj.run()
