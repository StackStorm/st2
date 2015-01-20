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

import os

from st2common.constants.meta import (ALLOWED_EXTS, PARSER_FUNCS)
from st2common import log as logging
from yaml.parser import ParserError

__all__ = [
    'ContentPackLoader',
    'MetaLoader'
]

LOG = logging.getLogger(__name__)


class ContentPackLoader(object):
    ALLOWED_CONTENT_TYPES = ['sensors', 'actions', 'rules']

    def get_content(self, base_dir, content_type):
        if content_type not in self.ALLOWED_CONTENT_TYPES:
            raise ValueError('Unsupported content_type: %s' % (content_type))

        if not os.path.isdir(base_dir):
            raise ValueError('Directory containing content-packs must be provided.')

        content = {}
        for pack in os.listdir(base_dir):
            pack_dir = os.path.join(base_dir, pack)
            new_content = None
            try:
                if content_type == 'sensors':
                    new_content = self._get_sensors(pack_dir)
                if content_type == 'actions':
                    new_content = self._get_actions(pack_dir)
                if content_type == 'rules':
                    new_content = self._get_rules(pack_dir)
            except:
                continue
            else:
                content[pack] = new_content

        return content

    def _get_sensors(self, pack):
        if 'sensors' not in os.listdir(pack):
            raise Exception('No sensors found.')
        return os.path.join(pack, 'sensors')

    def _get_actions(self, pack):
        if 'actions' not in os.listdir(pack):
            raise Exception('No actions found.')
        return os.path.join(pack, 'actions')

    def _get_rules(self, pack):
        if 'rules' not in os.listdir(pack):
            raise Exception('No rules found.')
        return os.path.join(pack, 'rules')


class MetaLoader(object):
    def load(self, file_path):
        """
        Loads content from file_path if file_path's extension
        is one of allowed ones (See ALLOWED_EXTS).

        Throws UnsupportedMetaException on disallowed filetypes.
        Throws ValueError on malformed meta.

        :param file_path: Absolute path to the file to load content from.
        :type file_path: ``str``

        :rtype: ``dict``
        """
        file_name, file_ext = os.path.splitext(file_path)

        if file_ext not in ALLOWED_EXTS:
            raise Exception('Unsupported meta type %s, file %s. Allowed: %s' %
                            (file_ext, file_path, ALLOWED_EXTS))

        return self._load(PARSER_FUNCS[file_ext], file_path)

    def _load(self, parser_func, file_path):
        with open(file_path, 'r') as fd:
            try:
                return parser_func(fd)
            except ValueError:
                LOG.exception('Failed loading content from %s.', file_path)
                raise
            except ParserError:
                LOG.exception('Failed loading content from %s.', file_path)
                raise
