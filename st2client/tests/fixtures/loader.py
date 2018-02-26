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

from __future__ import absolute_import
try:
    import simplejson as json
except ImportError:
    import json

import os
import six
import yaml


ALLOWED_EXTS = ['.json', '.yaml', '.yml', '.txt']
PARSER_FUNCS = {'.json': json.load, '.yml': yaml.safe_load, '.yaml': yaml.safe_load}


def get_fixtures_base_path():
    return os.path.dirname(__file__)


def load_content(file_path):
    """
    Loads content from file_path if file_path's extension
    is one of allowed ones (See ALLOWED_EXTS).
    Throws UnsupportedMetaException on disallowed filetypes.
    :param file_path: Absolute path to the file to load content from.
    :type file_path: ``str``
    :rtype: ``dict``
    """
    file_name, file_ext = os.path.splitext(file_path)

    if file_ext not in ALLOWED_EXTS:
        raise Exception('Unsupported meta type %s, file %s. Allowed: %s' %
                        (file_ext, file_path, ALLOWED_EXTS))

    parser_func = PARSER_FUNCS.get(file_ext, None)

    with open(file_path, 'r') as fd:
        return parser_func(fd) if parser_func else fd.read()


def load_fixtures(fixtures_dict=None):
    """
    Loads fixtures specified in fixtures_dict. This method must be
    used for fixtures that don't have associated data models. We
    simply want to load the meta into dict objects.
    fixtures_dict should be of the form:
    {
        'actionchains': ['actionchain1.json', 'actionchain2.json'],
        'workflows': ['workflow.yaml']
    }
    :param fixtures_dict: Dictionary specifying the fixtures to load for each type.
    :type fixtures_dict: ``dict``
    :rtype: ``dict``
    """
    if fixtures_dict is None:
        fixtures_dict = {}

    all_fixtures = {}
    fixtures_base_path = get_fixtures_base_path()
    for fixture_type, fixtures in six.iteritems(fixtures_dict):
        loaded_fixtures = {}
        for fixture in fixtures:
            fixture_path = fixtures_base_path + '/' + fixture
            fixture_dict = load_content(fixture_path)
            loaded_fixtures[fixture] = fixture_dict
        all_fixtures[fixture_type] = loaded_fixtures

    return all_fixtures
