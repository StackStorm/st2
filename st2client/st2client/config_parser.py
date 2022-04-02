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
Module for parsing CLI config file.
"""

from __future__ import absolute_import

import logging
import os

from collections import defaultdict

import io

import six
from six.moves.configparser import ConfigParser


__all__ = [
    "CLIConfigParser",
    "ST2_CONFIG_DIRECTORY",
    "ST2_CONFIG_PATH",
    "CONFIG_DEFAULT_VALUES",
]

ST2_CONFIG_DIRECTORY = "~/.st2"
ST2_CONFIG_DIRECTORY = os.path.abspath(os.path.expanduser(ST2_CONFIG_DIRECTORY))

ST2_CONFIG_PATH = os.path.abspath(os.path.join(ST2_CONFIG_DIRECTORY, "config"))

CONFIG_FILE_OPTIONS = {
    "general": {
        "base_url": {"type": "string", "default": None},
        "api_version": {"type": "string", "default": None},
        "cacert": {"type": "string", "default": None},
        "silence_ssl_warnings": {"type": "bool", "default": False},
        "silence_schema_output": {"type": "bool", "default": True},
    },
    "cli": {
        "debug": {"type": "bool", "default": False},
        "cache_token": {"type": "boolean", "default": True},
        "timezone": {"type": "string", "default": "UTC"},
    },
    "credentials": {
        "username": {"type": "string", "default": None},
        "password": {"type": "string", "default": None},
        "api_key": {"type": "string", "default": None},
        "basic_auth": {
            # Basic auth credentials in username:password notation
            "type": "string",
            "default": None,
        },
    },
    "api": {"url": {"type": "string", "default": None}},
    "auth": {"url": {"type": "string", "default": None}},
    "stream": {"url": {"type": "string", "default": None}},
}

CONFIG_DEFAULT_VALUES = {}

for section, keys in six.iteritems(CONFIG_FILE_OPTIONS):
    CONFIG_DEFAULT_VALUES[section] = {}

    for key, options in six.iteritems(keys):
        default_value = options["default"]
        CONFIG_DEFAULT_VALUES[section][key] = default_value


class CLIConfigParser(object):
    def __init__(
        self,
        config_file_path,
        validate_config_exists=True,
        validate_config_permissions=True,
        log=None,
    ):
        if validate_config_exists and not os.path.isfile(config_file_path):
            raise ValueError('Config file "%s" doesn\'t exist')

        if log is None:
            log = logging.getLogger(__name__)
            logging.basicConfig()

        self.config_file_path = config_file_path
        self.validate_config_permissions = validate_config_permissions
        self.LOG = log

    def parse(self):
        """
        Parse the config and return a dict with the parsed values.

        :rtype: ``dict``
        """
        result = defaultdict(dict)

        if not os.path.isfile(self.config_file_path):
            # Config doesn't exist, return the default values
            return CONFIG_DEFAULT_VALUES

        config_dir_path = os.path.dirname(self.config_file_path)

        if self.validate_config_permissions:
            # Make sure the directory permissions == 0o770
            if bool(os.stat(config_dir_path).st_mode & 0o7):
                self.LOG.warn(
                    "The StackStorm configuration directory permissions are "
                    "insecure (too permissive): others have access."
                )

            # Make sure the setgid bit is set on the directory
            if not bool(os.stat(config_dir_path).st_mode & 0o2000):
                self.LOG.info(
                    "The SGID bit is not set on the StackStorm configuration "
                    "directory."
                )

            # Make sure the file permissions == 0o660
            if bool(os.stat(self.config_file_path).st_mode & 0o7):
                self.LOG.warn(
                    "The StackStorm configuration file permissions are "
                    "insecure: others have access."
                )

        config = ConfigParser()
        with io.open(self.config_file_path, "r", encoding="utf8") as fp:
            config.readfp(fp)

        for section, keys in six.iteritems(CONFIG_FILE_OPTIONS):
            for key, options in six.iteritems(keys):
                key_type = options["type"]
                key_default_value = options["default"]

                if config.has_option(section, key):
                    if key_type in ["str", "string"]:
                        get_func = config.get
                    elif key_type in ["int", "integer"]:
                        get_func = config.getint
                    elif key_type in ["float"]:
                        get_func = config.getfloat
                    elif key_type in ["bool", "boolean"]:
                        get_func = config.getboolean
                    else:
                        msg = 'Invalid type "%s" for option "%s"' % (key_type, key)
                        raise ValueError(msg)

                    value = get_func(section, key, raw=True)
                    result[section][key] = value
                else:
                    result[section][key] = key_default_value

        return dict(result)
