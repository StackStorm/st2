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
import re

import jsonschema

from st2common.util import schema as util_schema
from st2common.constants.pack import MANIFEST_FILE_NAME
from st2common.constants.pack import PACK_REF_WHITELIST_REGEX
from st2common.content.loader import MetaLoader

__all__ = [
    'get_pack_ref_from_metadata',
    'get_pack_metadata',

    'validate_config_against_schema',

    'normalize_pack_version'
]


def get_pack_ref_from_metadata(metadata, pack_directory_name=None):
    """
    Utility function which retrieves pack "ref" attribute from the pack metadata file.

    If this attribute is not provided, an attempt is made to infer "ref" from the "name" attribute.

    :rtype: ``str``
    """
    pack_ref = None

    # The rules for the pack ref are as follows:
    # 1. If ref attribute is available, we used that
    # 2. If pack_directory_name is available we use that (this only applies to packs
    # which are in sub-directories)
    # 2. If attribute is not available, but pack name is and pack name meets the valid name
    # criteria, we use that
    if metadata.get('ref', None):
        pack_ref = metadata['ref']
    elif pack_directory_name and re.match(PACK_REF_WHITELIST_REGEX, pack_directory_name):
        pack_ref = pack_directory_name
    else:
        if re.match(PACK_REF_WHITELIST_REGEX, metadata['name']):
            pack_ref = metadata['name']
        else:
            msg = ('Pack name "%s" contains invalid characters and "ref" attribute is not '
                   'available. You either need to add "ref" attribute which contains only word '
                   'characters to the pack metadata file or update name attribute to contain only'
                   'word characters.')
            raise ValueError(msg % (metadata['name']))

    return pack_ref


def get_pack_metadata(pack_dir):
    """
    Return parsed metadata for a particular pack directory.

    :rtype: ``dict``
    """
    manifest_path = os.path.join(pack_dir, MANIFEST_FILE_NAME)

    if not os.path.isfile(manifest_path):
        raise ValueError('Pack "%s" is missing %s file' % (pack_dir, MANIFEST_FILE_NAME))

    meta_loader = MetaLoader()
    content = meta_loader.load(manifest_path)
    if not content:
        raise ValueError('Pack "%s" metadata file is empty' % (pack_dir))

    return content


def validate_config_against_schema(config_schema, config_object, config_path,
                                  pack_name=None):
    """
    Validate provided config dictionary against the provided config schema
    dictionary.
    """
    pack_name = pack_name or 'unknown'

    schema = util_schema.get_schema_for_resource_parameters(parameters_schema=config_schema,
                                                            allow_additional_properties=True)
    instance = config_object

    try:
        cleaned = util_schema.validate(instance=instance, schema=schema,
                                       cls=util_schema.CustomValidator, use_default=True,
                                       allow_default_none=True)
    except jsonschema.ValidationError as e:
        attribute = getattr(e, 'path', [])
        attribute = '.'.join(attribute)

        msg = ('Failed validating attribute "%s" in config for pack "%s" (%s): %s' %
               (attribute, pack_name, config_path, str(e)))
        raise jsonschema.ValidationError(msg)

    return cleaned


def normalize_pack_version(version):
    """
    Normalize old, pre StackStorm v2.1 non valid semver version string (e.g. 0.2) to a valid
    semver version string (0.2.0).

    :rtype: ``str``
    """
    version = str(version)

    version_seperator_count = version.count('.')
    if version_seperator_count == 1:
        version = version + '.0'

    return version
