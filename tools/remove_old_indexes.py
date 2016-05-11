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

import traceback

from pymongo import ASCENDING

from st2common import config
from st2common import script_setup
from st2common.models.db.actionalias import ActionAliasDB


INDEXES_TO_DROP = [
    # Dropped after v1.4
    (ActionAliasDB, 'name_%d' % ASCENDING)
]


def remove_old_indexes():
    for model, index_name in INDEXES_TO_DROP:
        collection = model._get_collection()
        try:
            print 'Dropping index "%s" from "%s"' % (index_name, collection.name)
            collection.drop_index(index_name)
        except:
            # maybe unnecessary but it is better to have this info to
            # begin with than not.
            traceback.print_exc()


def main():
    try:
        script_setup.setup(config, register_mq_exchanges=False)
        remove_old_indexes()
    finally:
        script_setup.teardown()


if __name__ == '__main__':
    main()
