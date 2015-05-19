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

import difflib
import json
import os
import pprint
import sys

import eventlet
from oslo.config import cfg

from st2common import config
from st2common.constants.pack import DEFAULT_PACK_NAME
from st2common.content.loader import ContentPackLoader
from st2common.content.loader import MetaLoader
from st2common.bootstrap.base import ResourceRegistrar
import st2common.content.utils as content_utils
from st2common.models.api.action import ActionAPI
from st2common.models.api.reactor import SensorTypeAPI
from st2common.models.api.rule import RuleAPI
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2common.models.system.common import ResourceReference
from st2common.persistence.reactor import SensorType, Rule
from st2common.persistence.action import Action

registrar = ResourceRegistrar()
registrar.ALLOWED_EXTENSIONS = ['.yaml', '.yml', '.json']

meta_loader = MetaLoader()
PP = pprint.PrettyPrinter(indent=2, depth=6, width=80)

API_MODELS_ARTIFACT_TYPES = {
    'actions': ActionAPI,
    'sensors': SensorTypeAPI,
    'rules': RuleAPI
}

API_MODELS_PERSISTENT_MODELS = {
    Action: ActionAPI,
    SensorType: SensorTypeAPI,
    Rule: RuleAPI
}


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


def _get_api_models_from_db(persistence_model, pack=None):
    filters = {}
    if pack:
        filters = {'pack': os.path.basename(os.path.normpath(pack))}
    models = persistence_model.query(**filters)
    models_dict = {}
    for model in models:
        model_pack = getattr(model, 'pack', None) or DEFAULT_PACK_NAME
        model_ref = ResourceReference.to_string_reference(name=model.name, pack=model_pack)
        if getattr(model, 'id', None):
            del model.id
        API_MODEL = API_MODELS_PERSISTENT_MODELS[persistence_model]
        models_dict[model_ref] = API_MODEL.from_model(model)
    return models_dict


def _get_api_models_from_disk(artifact_type, pack=None):
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
            if not artifact.get('pack', None):
                artifact['pack'] = pack_name
            ref = ResourceReference.to_string_reference(name=name,
                                                        pack=pack_name)
            API_MODEL = API_MODELS_ARTIFACT_TYPES[artifact_type]
            artifact_api = API_MODEL(**artifact)
            artifact_db = API_MODEL.to_model(artifact_api)
            artifact_api = API_MODEL.from_model(artifact_db)
            artifacts_dict[ref] = artifact_api

    return artifacts_dict


def _content_diff(artifact_type=None, artifact_in_disk=None, artifact_in_db=None):
    artifact_in_disk_str = json.dumps(
        artifact_in_disk.__json__(), sort_keys=True,
        indent=4, separators=(',', ': ')
    )
    artifact_in_db_str = json.dumps(
        artifact_in_db.__json__(), sort_keys=True,
        indent=4, separators=(',', ': ')
    )
    diffs = difflib.context_diff(artifact_in_db_str.splitlines(),
                                 artifact_in_disk_str.splitlines(),
                                 fromfile='DB contents', tofile='Disk contents')
    printed = False
    for diff in diffs:
        if not printed:
            print('###################################################################' +
                  '##########')
            identifier = getattr(artifact_in_db, 'ref', getattr(artifact_in_db, 'name'))
            print('%s %s in db differs from what is in disk.' % (artifact_type.upper(),
                  identifier))
            printed = True
        print(diff)


def _diff(persistence_model, artifact_type, pack=None, verbose=True,
          content_diff=True):
    artifacts_in_db_dict = _get_api_models_from_db(persistence_model, pack)
    artifacts_in_disk_dict = _get_api_models_from_disk(artifact_type, pack=pack)

    # print(artifacts_in_disk_dict)
    all_artifacts = set(artifacts_in_db_dict.keys() + artifacts_in_disk_dict.keys())

    for artifact in all_artifacts:
        artifact_in_db = artifacts_in_db_dict.get(artifact, None)
        artifact_in_disk = artifacts_in_disk_dict.get(artifact, None)
        artifact_in_disk_pretty_json = None
        artifact_in_db_pretty_json = None

        if verbose:
            print('******************************************************************************')
            print('Checking if artifact %s is present in both disk and db.' % artifact)
        if not artifact_in_db:
            print('##############################################################################')
            print('%s %s in disk not available in db.' % (artifact_type.upper(), artifact))
            artifact_in_disk_pretty_json = json.dumps(
                artifact_in_disk.__json__(), sort_keys=True,
                indent=4, separators=(',', ': ')
            )
            if verbose:
                print('File contents: \n')
                print(artifact_in_disk_pretty_json)
            continue

        if not artifact_in_disk:
            print('##############################################################################')
            print('%s %s in db not available in disk.' % (artifact_type.upper(), artifact))
            artifact_in_db_pretty_json = json.dumps(
                artifact_in_db.__json__(), sort_keys=True,
                indent=4, separators=(',', ': ')
            )
            if verbose:
                print('DB contents: \n')
                print(artifact_in_db_pretty_json)
            continue
        if verbose:
            print('Artifact %s exists in both disk and db.' % artifact)
        if content_diff:
            if verbose:
                print('Performing content diff for artifact %s.' % artifact)
            _content_diff(artifact_type=artifact_type,
                          artifact_in_disk=artifact_in_disk,
                          artifact_in_db=artifact_in_db)


def _diff_actions(pack=None, verbose=False, content_diff=True):
    _diff(Action, 'actions', pack=pack,
          verbose=verbose, content_diff=content_diff)


def _diff_sensors(pack=None, verbose=False, content_diff=True):
    _diff(SensorType, 'sensors', pack=pack,
          verbose=verbose, content_diff=content_diff)


def _diff_rules(pack=None, verbose=True, content_diff=True):
    _diff(Rule, 'rules', pack=pack,
          verbose=verbose, content_diff=content_diff)


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
        cfg.BoolOpt('verbose', default=False),
        cfg.BoolOpt('simple', default=False,
                    help='In simple mode, tool only tells you if content is missing.' +
                         'It doesn\'t show you content diff between disk and db.'),
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
    content_diff = not cfg.CONF.simple

    if cfg.CONF.all:
        _diff_sensors(pack=pack, verbose=cfg.CONF.verbose, content_diff=content_diff)
        _diff_actions(pack=pack, verbose=cfg.CONF.verbose, content_diff=content_diff)
        _diff_rules(pack=pack, verbose=cfg.CONF.verbose, content_diff=content_diff)
        return

    if cfg.CONF.sensors:
        _diff_sensors(pack=pack, verbose=cfg.CONF.verbose, content_diff=content_diff)

    if cfg.CONF.actions:
        _diff_actions(pack=pack, verbose=cfg.CONF.verbose, content_diff=content_diff)

    if cfg.CONF.rules:
        _diff_rules(pack=pack, verbose=cfg.CONF.verbose, content_diff=content_diff)

    # Disconnect from db.
    db_teardown()

if __name__ == '__main__':
    main()
