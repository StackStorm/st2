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

from oslo_config import cfg, types

from st2common import config as st2cfg
from st2common.constants.sensors import DEFAULT_PARTITION_LOADER
from st2common.constants.system import VERSION_STRING
from st2common.constants.system import DEFAULT_CONFIG_FILE_PATH

CONF = cfg.CONF


def parse_args(args=None):
    st2cfg.use_st2_env_vars(cfg.CONF)
    cfg.CONF(
        args=args,
        version=VERSION_STRING,
        default_config_files=[DEFAULT_CONFIG_FILE_PATH],
    )


def register_opts(ignore_errors=False):
    _register_common_opts(ignore_errors=ignore_errors)
    _register_sensor_container_opts(ignore_errors=ignore_errors)


def get_logging_config_path():
    return cfg.CONF.sensorcontainer.logging


def _register_common_opts(ignore_errors=False):
    st2cfg.register_opts(ignore_errors=ignore_errors)


def _register_sensor_container_opts(ignore_errors=False):
    logging_opts = [
        cfg.StrOpt(
            "logging",
            default="/etc/st2/logging.sensorcontainer.conf",
            help="location of the logging.conf file",
        )
    ]

    st2cfg.do_register_opts(
        logging_opts, group="sensorcontainer", ignore_errors=ignore_errors
    )

    # Partitioning options
    partition_opts = [
        cfg.StrOpt(
            "sensor_node_name", default="sensornode1", help="name of the sensor node."
        ),
        cfg.Opt(
            "partition_provider",
            type=types.Dict(value_type=types.String()),
            default={"name": DEFAULT_PARTITION_LOADER},
            help="Provider of sensor node partition config.",
        ),
    ]

    st2cfg.do_register_opts(
        partition_opts, group="sensorcontainer", ignore_errors=ignore_errors
    )

    # Other options
    other_opts = [
        cfg.BoolOpt(
            "single_sensor_mode",
            default=False,
            help="Run in a single sensor mode where parent process exits when a sensor crashes / "
            "dies. This is useful in environments where partitioning, sensor process life "
            "cycle and failover is handled by a 3rd party service such as kubernetes.",
        )
    ]

    st2cfg.do_register_opts(
        other_opts, group="sensorcontainer", ignore_errors=ignore_errors
    )

    # CLI options
    cli_opts = [
        cfg.StrOpt(
            "sensor-ref",
            help="Only run sensor with the provided reference. Value is of the form "
            "<pack>.<sensor-name> (e.g. linux.FileWatchSensor).",
        ),
        cfg.BoolOpt(
            "single-sensor-mode",
            default=False,
            help="Run in a single sensor mode where parent process exits when a sensor crashes / "
            "dies. This is useful in environments where partitioning, sensor process life "
            "cycle and failover is handled by a 3rd party service such as kubernetes.",
        ),
    ]

    st2cfg.do_register_cli_opts(cli_opts, ignore_errors=ignore_errors)


register_opts(ignore_errors=True)
