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

from st2common import log as logging
from st2common.services.keyvalues import get_key_reference
from st2common.constants.keyvalue import USER_SCOPE
from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.util.crypto import symmetric_decrypt
from st2common.models.api.keyvalue import KeyValuePairAPI
from st2common.persistence.keyvalue import KeyValuePair

__all__ = [
    'set_datastore_value_for_config_key',
]

LOG = logging.getLogger(__name__)


def set_datastore_value_for_config_key(pack_name, key_name, value, secret=False, user=None):
    """
    Set config value in the datastore.

    This function takes care of correctly encoding the key name, serializing the
    value, etc.

    :param pack_name: Pack name.
    :type pack_name: ``str``

    :param key_name: Config key name.
    :type key_name: ``str``

    :param secret: True if this value is a secret.
    :type secret: ``bool``

    :param user: Optional username if working on a user-scoped config item.
    :type user: ``str``

    :rtype: :class:`KeyValuePairDB`
    """

    if user:
        scope = USER_SCOPE
    else:
        scope = SYSTEM_SCOPE

    name = get_key_reference(scope=scope, name=key_name, user=user)

    kvp_api = KeyValuePairAPI(name=name, value=value, scope=scope, secret=secret)
    kvp_db = KeyValuePairAPI.to_model(kvp_api)

    # TODO: Obtain a lock
    existing_kvp_db = KeyValuePair.get_by_scope_and_name(scope=scope, name=name)
    if existing_kvp_db:
        kvp_db.id = existing_kvp_db.id

    kvp_db = KeyValuePair.add_or_update(kvp_db)
    return kvp_db


def deserialize_key_value(value, secret=False):
    """
    Deserialize the datastore item value.

    Note: Right now only strings as supported so only thing this function does is it decrypts
    secret values.

    :param value: Value to deserialize.
    :type value: ``str``

    :param secret: True if a value is a secret and is encrypted.
    :type secret: ``bool``
    """
    if secret:
        KeyValuePairAPI._setup_crypto()
        value = symmetric_decrypt(KeyValuePairAPI.crypto_key, value)

    return value
