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

Tags: Ops tool.

A utility script that diffs models registered in st2 db versus what's on disk.

"""

import os
import sys

import eventlet
from oslo.config import cfg

from st2common import config
from st2common.constants.pack import DEFAULT_PACK_NAME
from st2common.content.loader import ContentPackLoader
from st2common.content.loader import MetaLoader
from st2common.bootstrap.base import ResourceRegistrar
import st2common.content.utils as content_utils
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2common.models.system.common import ResourceReference
from st2common.persistence.reactor import SensorType, Rule
from st2common.persistence.action import Action

registrar = ResourceRegistrar()
registrar.ALLOWED_EXTENSIONS = ['.yaml', '.yml', '.json']

meta_loader = MetaLoader()


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


def _get_models_from_db(persistence_model, pack=None):
    filters = {}
    if pack:
        filters = {'pack': os.path.basename(os.path.normpath(pack))}
    models = persistence_model.query(**filters)
    models_dict = {}
    for model in models:
        model_pack = getattr(model, 'pack', None) or DEFAULT_PACK_NAME
        model_ref = ResourceReference.to_string_reference(name=model.name, pack=model_pack)
        models_dict[model_ref] = model
    return models_dict


def _get_models_from_disk(artifact_type, pack=None):
    loader = ContentPackLoader()
    artifacts = None

    if pack:
        artifacts = loader.get_content_from_pack(pack, artifact_type)
    else:
        packs_dirs = content_utils.get_packs_base_paths()
        artifacts = loader.get_content(packs_dirs, artifact_type)

    artifacts_dict = {}
    for pack_name, pack_path in artifacts.items():
        artifacts_paths = registrar.get_resources_from_pack(pack_path)
        for artifact_path in artifacts_paths:
            artifact = meta_loader.load(artifact_path)
            name = artifact.get('name', None) or artifact.get('class_name', None)
            ref = ResourceReference.to_string_reference(name=name,
                                                        pack=pack_name)
            artifacts_dict[ref] = artifact
    return artifacts_dict


def _simple_diff(persistence_model, artifact_type, pack=None):
    artifacts_in_db_dict = _get_models_from_db(persistence_model, pack)
    artifacts_in_disk_dict = _get_models_from_disk(artifact_type, pack=pack)

    # print(artifacts_in_disk_dict)
    all_artifacts = set(artifacts_in_db_dict.keys() + artifacts_in_disk_dict.keys())

    for artifact in all_artifacts:
        artifact_in_db = artifacts_in_db_dict.get(artifact, None)
        artifact_in_disk = artifacts_in_disk_dict.get(artifact, None)
        if not artifact_in_db:
            print('%s %s in disk not available in db.' % (artifact_type, artifact))
        if not artifact_in_disk:
            print('%s %s in db not available in disk.' % (artifact_type, artifact))


def _diff_actions(pack=None):
    _simple_diff(Action, 'actions', pack=pack)


def _diff_sensors(pack=None):
    _simple_diff(SensorType, 'sensors', pack=pack)


def _diff_rules(pack=None):
    _simple_diff(Rule, 'rules', pack=pack)


def main():
    _monkey_patch()

    cli_opts = [
        cfg.BoolOpt('sensors', default=False,
                    help='diff sensor alone.'),
        cfg.BoolOpt('actions', default=False,
                    help='diff actions alone.'),
        cfg.BoolOpt('rules', default=False,
                    help='diff rules alone.'),
        cfg.BoolOpt('all', default=False,
                    help='diff sensors, actions and rules.'),
        cfg.StrOpt('pack', default=None, help='Path to specific pack to diff.')
    ]
    do_register_cli_opts(cli_opts)
    config.parse_args()

    username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
    password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None

    # Connect to db.
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
             username=username, password=password)

    # Diff content
    pack = cfg.CONF.pack or None

    if cfg.CONF.all:
        _diff_sensors(pack=pack)
        _diff_actions(pack=pack)
        _diff_rules(pack=pack)
        return

    if cfg.CONF.sensors:
        _diff_sensors(pack=pack)

    if cfg.CONF.actions:
        _diff_actions(pack=pack)

    if cfg.CONF.rules:
        _diff_rules(pack=pack)

    # Disconnect from db.
    db_teardown()

if __name__ == '__main__':
    main()
