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
from st2common.services.keyvalues import KeyValueLookup


class TestKeyValueLookup(CleanDbTestCase):

    def test_non_hierarchical_lookup(self):
        k1 = KeyValuePair.add_or_update(KeyValuePairDB(name='k1', value='v1'))
        k2 = KeyValuePair.add_or_update(KeyValuePairDB(name='k2', value='v2'))
        k3 = KeyValuePair.add_or_update(KeyValuePairDB(name='k3', value='v3'))

        lookup = KeyValueLookup()
        self.assertEquals(str(lookup.k1), k1.value)
        self.assertEquals(str(lookup.k2), k2.value)
        self.assertEquals(str(lookup.k3), k3.value)

    def test_hierarchical_lookup_dotted(self):
        k1 = KeyValuePair.add_or_update(KeyValuePairDB(name='a.b', value='v1'))
        k2 = KeyValuePair.add_or_update(KeyValuePairDB(name='a.b.c', value='v2'))
        k3 = KeyValuePair.add_or_update(KeyValuePairDB(name='b.c', value='v3'))

        lookup = KeyValueLookup()
        self.assertEquals(str(lookup.a.b), k1.value)
        self.assertEquals(str(lookup.a.b.c), k2.value)
        self.assertEquals(str(lookup.b.c), k3.value)
        self.assertEquals(str(lookup.a), '')

    def test_hierarchical_lookup_dict(self):
        k1 = KeyValuePair.add_or_update(KeyValuePairDB(name='a.b', value='v1'))
        k2 = KeyValuePair.add_or_update(KeyValuePairDB(name='a.b.c', value='v2'))
        k3 = KeyValuePair.add_or_update(KeyValuePairDB(name='b.c', value='v3'))

        lookup = KeyValueLookup()
        self.assertEquals(str(lookup['a']['b']), k1.value)
        self.assertEquals(str(lookup['a']['b']['c']), k2.value)
        self.assertEquals(str(lookup['b']['c']), k3.value)
        self.assertEquals(str(lookup['a']), '')

    def test_missing_key_lookup(self):
        lookup = KeyValueLookup()
        self.assertEquals(str(lookup.missing_key), '')
        self.assertTrue(lookup.missing_key, 'Should be not none.')
