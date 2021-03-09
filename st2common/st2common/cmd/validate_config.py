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
Script for validating a config file against a a particular config schema.
"""

from __future__ import absolute_import

import os

import yaml
import six
from oslo_config import cfg

from st2common.config import do_register_cli_opts
from st2common.constants.system import VERSION_STRING
from st2common.constants.exit_codes import SUCCESS_EXIT_CODE
from st2common.constants.exit_codes import FAILURE_EXIT_CODE
from st2common.util.pack import validate_config_against_schema

__all__ = ["main"]


def _do_register_cli_opts(opts, ignore_errors=False):
    for opt in opts:
        try:
            cfg.CONF.register_cli_opt(opt)
        except:
            if not ignore_errors:
                raise


def _register_cli_opts():
    cli_opts = [
        cfg.StrOpt(
            "schema-path",
            default=None,
            required=True,
            help="Path to the config schema to use for validation.",
        ),
        cfg.StrOpt(
            "config-path",
            default=None,
            required=True,
            help="Path to the config file to validate.",
        ),
    ]

    do_register_cli_opts(cli_opts)


def main():
    _register_cli_opts()
    cfg.CONF(args=None, version=VERSION_STRING)

    schema_path = os.path.abspath(cfg.CONF.schema_path)
    config_path = os.path.abspath(cfg.CONF.config_path)

    print('Validating config "%s" against schema in "%s"' % (config_path, schema_path))

    with open(schema_path, "r") as fp:
        config_schema = yaml.safe_load(fp.read())

    with open(config_path, "r") as fp:
        config_object = yaml.safe_load(fp.read())

    try:
        validate_config_against_schema(
            config_schema=config_schema,
            config_object=config_object,
            config_path=config_path,
        )
    except Exception as e:
        print("Failed to validate pack config.\n%s" % six.text_type(e))
        return FAILURE_EXIT_CODE

    print(
        'Config "%s" successfully validated against schema in %s.'
        % (config_path, schema_path)
    )
    return SUCCESS_EXIT_CODE
