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

import six
from yaml.parser import ParserError

from st2common.constants.meta import (ALLOWED_EXTS, PARSER_FUNCS)
from st2common import log as logging

__all__ = [
    'ContentPackLoader',
    'MetaLoader'
]

LOG = logging.getLogger(__name__)


class ContentPackLoader(object):
    ALLOWED_CONTENT_TYPES = ['sensors', 'actions', 'rules']

    def get_content(self, base_dirs, content_type):
        """
        Retrieve content from the provided directories.

        Provided directories are searched from left to right. If a pack with the same name exists
        in multiple directories, first pack which is found wins.

        :param base_dirs: Directories to look into.
        :type base_dirs: ``list``

        :param content_type: Content type to look for (sensors, actions, rules).
        :type content_type: ``str``

        :rtype: ``dict``
        """
        assert(isinstance(base_dirs, list))

        if content_type not in self.ALLOWED_CONTENT_TYPES:
            raise ValueError('Unsupported content_type: %s' % (content_type))

        content = {}
        pack_to_dir_map = {}
        for base_dir in base_dirs:
            if not os.path.isdir(base_dir):
                raise ValueError('Directory "%s" doesn\'t exist' % (base_dir))

            dir_content = self._get_content_from_dir(base_dir=base_dir, content_type=content_type)

            # Check for duplicate packs
            for pack_name, pack_content in six.iteritems(dir_content):
                if pack_name in content:
                    pack_dir = pack_to_dir_map[pack_name]
                    LOG.warning('Pack "%s" already found in "%s", ignoring content from "%s"' %
                                (pack_name, pack_dir, base_dir))
                else:
                    content[pack_name] = pack_content
                    pack_to_dir_map[pack_name] = base_dir

        return content

    def _get_content_from_dir(self, base_dir, content_type):
        if content_type == 'sensors':
            get_func = self._get_sensors
        elif content_type == 'actions':
            get_func = self._get_actions
        elif content_type == 'rules':
            get_func = self._get_rules

        content = {}
        for pack in os.listdir(base_dir):
            # TODO: Use function from util which escapes the name
            pack_dir = os.path.join(base_dir, pack)

            pack_content = None
            try:
                pack_content = get_func(pack_dir=pack_dir)
            except ValueError:
                continue
            else:
                content[pack] = pack_content

        return content

    def _get_sensors(self, pack_dir):
        if 'sensors' not in os.listdir(pack_dir):
            raise ValueError('No sensors found.')
        return os.path.join(pack_dir, 'sensors')

    def _get_actions(self, pack_dir):
        if 'actions' not in os.listdir(pack_dir):
            raise ValueError('No actions found.')
        return os.path.join(pack_dir, 'actions')

    def _get_rules(self, pack_dir):
        if 'rules' not in os.listdir(pack_dir):
            raise ValueError('No rules found.')
        return os.path.join(pack_dir, 'rules')


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
