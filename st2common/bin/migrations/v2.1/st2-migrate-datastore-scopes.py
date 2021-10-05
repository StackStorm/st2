#!/usr/bin/env python
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
import sys
import traceback as tb

from st2common import config
from st2common.constants.keyvalue import FULL_SYSTEM_SCOPE, SYSTEM_SCOPE
from st2common.constants.keyvalue import FULL_USER_SCOPE, USER_SCOPE
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
from st2common.service_setup import db_setup
from st2common.service_setup import db_teardown


def migrate_datastore():
    key_value_items = KeyValuePair.get_all()

    try:
        for kvp in key_value_items:
            kvp_id = getattr(kvp, "id", None)
            secret = getattr(kvp, "secret", False)
            scope = getattr(kvp, "scope", SYSTEM_SCOPE)

            if scope == USER_SCOPE:
                scope = FULL_USER_SCOPE

            if scope == SYSTEM_SCOPE:
                scope = FULL_SYSTEM_SCOPE

            new_kvp_db = KeyValuePairDB(
                id=kvp_id,
                name=kvp.name,
                expire_timestamp=kvp.expire_timestamp,
                value=kvp.value,
                secret=secret,
                scope=scope,
            )
            KeyValuePair.add_or_update(new_kvp_db)
    except:
        print("ERROR: Failed migrating datastore item with name: %s" % kvp.name)
        tb.print_exc()
        raise


def main():
    config.parse_args()

    # Connect to db.
    db_setup()

    # Migrate rules.
    try:
        migrate_datastore()
        print("SUCCESS: Datastore items migrated successfully.")
        exit_code = 0
    except:
        print("ABORTED: Datastore migration aborted on first failure.")
        exit_code = 1

    # Disconnect from db.
    db_teardown()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
