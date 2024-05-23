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

import os

from yaml.parser import ParserError
import six

from oslo_config import cfg
from st2common import log as logging
from st2common.constants.meta import ALLOWED_EXTS
from st2common.constants.meta import PARSER_FUNCS
from st2common.constants.pack import MANIFEST_FILE_NAME

if six.PY2:
    from io import open

__all__ = ["ContentPackLoader", "MetaLoader", "OverrideLoader"]

LOG = logging.getLogger(__name__)


class ContentPackLoader(object):
    """
    Class for loading pack and pack content information from directories on disk.
    """

    # TODO: Rename "get_content" methods since they don't actually return
    # content - they just return a path

    ALLOWED_CONTENT_TYPES = [
        "triggers",
        "sensors",
        "actions",
        "rules",
        "aliases",
        "policies",
    ]

    def get_packs(self, base_dirs):
        """
        Retrieve a list of packs in the provided directories.

        :return: Dictionary where the key is pack name and the value is full path to the pack
                 directory.
        :rtype: ``dict``
        """
        if not isinstance(base_dirs, list):
            raise TypeError(
                "The base dirs has a value that is not a list"
                f" (was {type(base_dirs)})."
            )

        result = {}
        for base_dir in base_dirs:
            if not os.path.isdir(base_dir):
                raise ValueError('Directory "%s" doesn\'t exist' % (base_dir))

            packs_in_dir = self._get_packs_from_dir(base_dir=base_dir)
            result.update(packs_in_dir)

        return result

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
        if not isinstance(base_dirs, list):
            raise TypeError(
                "The base dirs has a value that is not a list"
                f" (was {type(base_dirs)})."
            )

        if content_type not in self.ALLOWED_CONTENT_TYPES:
            raise ValueError("Unsupported content_type: %s" % (content_type))

        content = {}
        pack_to_dir_map = {}
        for base_dir in base_dirs:
            if not os.path.isdir(base_dir):
                raise ValueError('Directory "%s" doesn\'t exist' % (base_dir))

            dir_content = self._get_content_from_dir(
                base_dir=base_dir, content_type=content_type
            )

            # Check for duplicate packs
            for pack_name, pack_content in six.iteritems(dir_content):
                if pack_name in content:
                    pack_dir = pack_to_dir_map[pack_name]
                    LOG.warning(
                        'Pack "%s" already found in "%s", ignoring content from "%s"'
                        % (pack_name, pack_dir, base_dir)
                    )
                else:
                    content[pack_name] = pack_content
                    pack_to_dir_map[pack_name] = base_dir

        return content

    def get_content_from_pack(self, pack_dir, content_type):
        """
        Retrieve content from the provided pack directory.

        :param pack_dir: Path to the pack directory.
        :type pack_dir: ``str``

        :param content_type: Content type to look for (sensors, actions, rules).
        :type content_type: ``str``

        :rtype: ``str``
        """
        if content_type not in self.ALLOWED_CONTENT_TYPES:
            raise ValueError("Unsupported content_type: %s" % (content_type))

        if not os.path.isdir(pack_dir):
            raise ValueError('Directory "%s" doesn\'t exist' % (pack_dir))

        content = self._get_content_from_pack_dir(
            pack_dir=pack_dir, content_type=content_type
        )
        return content

    def _get_packs_from_dir(self, base_dir):
        result = {}
        for pack_name in os.listdir(base_dir):
            if pack_name == "__pycache__":
                continue
            pack_dir = os.path.join(base_dir, pack_name)
            pack_manifest_file = os.path.join(pack_dir, MANIFEST_FILE_NAME)

            if os.path.isdir(pack_dir) and os.path.isfile(pack_manifest_file):
                result[pack_name] = pack_dir

        return result

    def _get_content_from_dir(self, base_dir, content_type):
        content = {}
        for pack in os.listdir(base_dir):
            if pack == "__pycache__":
                continue
            # TODO: Use function from util which escapes the name
            pack_dir = os.path.join(base_dir, pack)

            # Ignore missing or non directories
            try:
                pack_content = self._get_content_from_pack_dir(
                    pack_dir=pack_dir, content_type=content_type
                )
            except ValueError:
                continue
            else:
                content[pack] = pack_content

        return content

    def _get_content_from_pack_dir(self, pack_dir, content_type):
        content_types = dict(
            triggers=self._get_triggers,
            sensors=self._get_sensors,
            actions=self._get_actions,
            rules=self._get_rules,
            aliases=self._get_aliases,
            policies=self._get_policies,
        )

        get_func = content_types.get(content_type)

        if get_func is None:
            raise ValueError("Invalid content_type: %s" % (content_type))

        if not os.path.isdir(pack_dir):
            raise ValueError('Directory "%s" doesn\'t exist' % (pack_dir))

        pack_content = get_func(pack_dir=pack_dir)
        return pack_content

    def _get_triggers(self, pack_dir):
        return self._get_folder(pack_dir=pack_dir, content_type="triggers")

    def _get_sensors(self, pack_dir):
        return self._get_folder(pack_dir=pack_dir, content_type="sensors")

    def _get_actions(self, pack_dir):
        return self._get_folder(pack_dir=pack_dir, content_type="actions")

    def _get_rules(self, pack_dir):
        return self._get_folder(pack_dir=pack_dir, content_type="rules")

    def _get_aliases(self, pack_dir):
        return self._get_folder(pack_dir=pack_dir, content_type="aliases")

    def _get_policies(self, pack_dir):
        return self._get_folder(pack_dir=pack_dir, content_type="policies")

    def _get_folder(self, pack_dir, content_type):
        path = os.path.join(pack_dir, content_type)
        if not os.path.isdir(path):
            return None
        return path


class MetaLoader(object):
    """
    Class for loading and parsing pack and resource metadata files.
    """

    def load(self, file_path, expected_type=None):
        """
        Loads content from file_path if file_path's extension
        is one of allowed ones (See ALLOWED_EXTS).

        Throws UnsupportedMetaException on disallowed filetypes.
        Throws ValueError on malformed meta.

        :param file_path: Absolute path to the file to load content from.
        :type file_path: ``str``

        :param expected_type: Expected type for the loaded and parsed content (optional).
        :type expected_type: ``object``

        :rtype: ``dict``
        """
        file_name, file_ext = os.path.splitext(file_path)

        if file_ext not in ALLOWED_EXTS:
            raise Exception(
                "Unsupported meta type %s, file %s. Allowed: %s"
                % (file_ext, file_path, ALLOWED_EXTS)
            )

        result = self._load(PARSER_FUNCS[file_ext], file_path)

        if expected_type and not isinstance(result, expected_type):
            actual_type = type(result).__name__
            error = 'Expected "%s", got "%s"' % (expected_type.__name__, actual_type)
            raise ValueError(error)

        return result

    def _load(self, parser_func, file_path):
        with open(file_path, "r", encoding="utf-8") as fd:
            try:
                return parser_func(fd)
            except ValueError:
                LOG.exception("Failed loading content from %s.", file_path)
                raise
            except ParserError:
                LOG.exception("Failed loading content from %s.", file_path)
                raise


class OverrideLoader(object):
    """
    Class for loading pack override data
    """

    # Mapping of permitted override types to resource name
    ALLOWED_OVERRIDE_TYPES = {
        "sensors": "class_name",
        "actions": "name",
        "rules": "name",
        "aliases": "name",
    }

    ALLOWED_OVERRIDE_NAMES = [
        "enabled",
    ]

    DEFAULT_OVERRIDE_VALUES = {"enabled": True}

    def override(self, pack_name, resource_type, content):

        """
        Loads override content for pack, and updates content

        :param pack_name: Name of pack
        :type pack_name: ``str``
        :param resource_type: Type of resource loading
        :type type: ``str``
        :param content: Content as loaded from meta information
        :type content: ``object``
        :return: Whether data was overridden
        :rtype: ``bool``
        """
        orig_content = content.copy()
        if resource_type not in self.ALLOWED_OVERRIDE_TYPES.keys():
            raise ValueError(
                f"Invalid override type of {resource_type} attempted for pack {pack_name}"
            )

        override_dir = os.path.join(cfg.CONF.system.base_path, "overrides")
        # Apply global overrides
        global_file = os.path.join(override_dir, "_global.yaml")
        self._apply_override_file(global_file, pack_name, resource_type, content, True)

        # Apply pack overrides
        override_file = os.path.join(override_dir, f"{pack_name}.yaml")
        self._apply_override_file(
            override_file, pack_name, resource_type, content, False
        )
        if content == orig_content:
            overridden = False
        else:
            # Need to account for defaults that might not have been set
            for key in self.ALLOWED_OVERRIDE_NAMES:
                if key not in orig_content.keys() and key in content.keys():
                    orig_content[key] = self.DEFAULT_OVERRIDE_VALUES[key]
            if content == orig_content:
                overridden = False
            else:
                overridden = True
        return overridden

    def _apply_override_file(
        self, override_file, pack_name, resource_type, content, global_file
    ):

        """
        Loads override content from override file

        :param override_file: Override filename
        :type override_file: ``str``
        :param pack_name: Name of pack
        :type pack_name: ``str``
        :param resource_type: Type of resource loading
        :type type: ``str``
        :param content: Content as loaded from meta information
        :type content: ``object``
        """

        if not os.path.exists(override_file):
            # No override file for pack
            LOG.debug(f"No override file {override_file} found")
            return

        # Read override file
        file_name, file_ext = os.path.splitext(override_file)
        overrides = self._load(PARSER_FUNCS[file_ext], override_file)
        # Apply overrides
        if resource_type in overrides:
            type_override = overrides[resource_type]
            name = content[self.ALLOWED_OVERRIDE_TYPES[resource_type]]
            if "defaults" in type_override:
                for key in type_override["defaults"]:
                    if key in self.ALLOWED_OVERRIDE_NAMES:
                        content[key] = type_override["defaults"][key]
                        LOG.debug(
                            f"Overridden {resource_type} {pack_name}.{name} {key} to default value of {content[key]} from {override_file}"
                        )
                    else:
                        raise ValueError(
                            f"Override attempted with invalid default key {key} in pack {pack_name}"
                        )

            if global_file:
                # No exceptions required in global content file
                return

            if "exceptions" in type_override:
                if name in type_override["exceptions"]:
                    for key in type_override["exceptions"][name]:
                        if key in self.ALLOWED_OVERRIDE_NAMES:
                            content[key] = type_override["exceptions"][name][key]
                            LOG.debug(
                                f"Overridden {resource_type} {pack_name}.{name} {key} to exception value of {content[key]} from {override_file}"
                            )
                        else:
                            raise ValueError(
                                f"Override attempted with invalid exceptions key {key} in pack {pack_name}"
                            )

    def _load(self, parser_func, file_path):
        with open(file_path, "r", encoding="utf-8") as fd:
            try:
                return parser_func(fd)
            except ValueError:
                LOG.exception("Failed loading content from %s.", file_path)
                raise
            except ParserError:
                LOG.exception("Failed loading content from %s.", file_path)
                raise
