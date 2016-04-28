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
Service functions for managing pack configuration inside the datastore.
"""

import json

from st2common import log as logging
from st2common.services import keyvalues as keyvalue_service
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
from st2common.constants.datastore import DATASTORE_KEY_SEPARATOR

__all__ = [
    'get_datastore_key_name',

    'get_datastore_value_for_config_key',
    'set_datastore_value_for_config_key',

    'get_datastore_value'
]

LOG = logging.getLogger(__name__)

# Prefix for datastore items which store config values
# Full keys follow this format: system.pack_config.<pack name>.<config key name>
# For example:
# pack_config.aws.setup.region
DATASTORE_CONFIG_KEY_PREFIX = ['pack_config']
DATASTORE_CONFIG_KEY_PREFIX = DATASTORE_KEY_SEPARATOR.join(DATASTORE_CONFIG_KEY_PREFIX)


def get_datastore_key_name(pack_name, key_name):
    """
    Retrieve datastore key name based on the config key name.
    """
    values = []
    values.append(DATASTORE_CONFIG_KEY_PREFIX)
    values.append(pack_name)
    values.append(key_name)

    return DATASTORE_KEY_SEPARATOR.join(values)


def get_datastore_value_for_config_key(pack_name, key_name):
    """
    Retrieve config value for the provided config key from the datastore.

    :param pack_name: Pack name.
    :type pack_name: ``str``

    :param key_name: Config key name.
    :type key_name: ``str``
    """
    name = get_datastore_key_name(pack_name=pack_name, key_name=key_name)
    kvp_db = get_datastore_value(key_name=name)
    return kvp_db


def get_datastore_value(key_name):
    """
    Retrieve config value with the matching datastore key name.

    :param key_name: Full key name in the datastore. Note: This must already be the fully qualified
                     name of the key in the datastore.
    :tupe key_name: ``str``
    """
    kvp_db = keyvalue_service.get_kvp_for_name(name=key_name)

    if not kvp_db:
        # Item doesn't exist
        return None

    if not kvp_db.value:
        # Item doesn't contain a value
        return None

    value = deserialize_key_value(kvp_db=kvp_db)
    return value


def set_datastore_value_for_config_key(pack_name, key_name, value):
    """
    Set config value in the datastore.

    This function takes care of correctly encoding the key name, serializing the
    value, etc.

    :param pack_name: Pack name.
    :type pack_name: ``str``

    :param key_name: Config key name.
    :type key_name: ``str``

    :rtype: :class:`KeyValuePairDB`
    """
    # TODO: Once and if config schema is available, validate the provided type against the one
    # specified in the schema.
    name = get_datastore_key_name(pack_name=pack_name, key_name=key_name)
    value = json.dumps({'value': value})
    kvp_db = KeyValuePairDB(name=name, value=value)
    kvp_db = KeyValuePair.add_or_update(kvp_db)

    return kvp_db


def deserialize_key_value(kvp_db):
    """
    Deserialize the datastore item value.

    Values are serialized as a JSON object where the actual value is stored under top-level key
    value.

    This introduces some space-related overhead, but it's transparent and preferred over custom
    serialization format.
    """
    try:
        value = json.loads(kvp_db.value)
    except Exception as e:
        # Value is not serialized correctly
        LOG.debug('Failed to de-serialize datastore item "%s": %s' % (kvp_db.name, str(e)),
                  exc_info=True)
        return None

    try:
        value = value['value']
    except KeyError:
        # Value is not serialized correctly
        LOG.debug('Datastore item "%s" is missing "value" attribute' % (kvp_db.name),
                  exc_info=True)
        return None

    return value
