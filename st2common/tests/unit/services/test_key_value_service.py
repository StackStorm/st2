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

from st2tests.base import CleanDbTestCase
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
from st2common.services import keyvalues as keyvalue_services

__all__ = [
    'KeyValueServicesTestCase'
]


class KeyValueServicesTestCase(CleanDbTestCase):
    def setUp(self):
        super(KeyValueServicesTestCase, self).setUp()

        # Insert mock DB objects
        kvp_1_db = KeyValuePairDB(name='a', value='valuea')
        kvp_1_db = KeyValuePair.add_or_update(kvp_1_db)

        kvp_2_db = KeyValuePairDB(name='b', value='valueb')
        kvp_2_db = KeyValuePair.add_or_update(kvp_2_db)

        kvp_3_db = KeyValuePairDB(name='c', value='valuec')
        kvp_3_db = KeyValuePair.add_or_update(kvp_3_db)

    def test_get_values_for_names(self):
        # All values are present in the database
        names = ['a', 'b', 'c']

        result = keyvalue_services.get_values_for_names(names=names)
        self.assertEqual(result, {'a': 'valuea', 'b': 'valueb', 'c': 'valuec'})

        # Not all the values are present in the database
        names = ['a', 'd', 'b', 'f']
        result = keyvalue_services.get_values_for_names(names=names)
        self.assertEqual(result, {'a': 'valuea', 'd': None, 'b': 'valueb', 'f': None})
