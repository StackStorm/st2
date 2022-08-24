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
import math
from random_words import RandomWords

from st2reactor.container.hash_partitioner import HashPartitioner, Range
from st2tests import config
from st2tests import DbTestCase
from st2tests.fixtures.generic.fixture import PACK_NAME as PACK
from st2tests.fixturesloader import FixturesLoader

FIXTURES_1 = {"sensors": ["sensor1.yaml", "sensor2.yaml", "sensor3.yaml"]}


class HashPartitionerTest(DbTestCase):

    models = None

    @classmethod
    def setUpClass(cls):
        super(HashPartitionerTest, cls).setUpClass()
        # Create TriggerTypes before creation of Rule to avoid failure. Rule requires the
        # Trigger and therefore TriggerType to be created prior to rule creation.
        cls.models = FixturesLoader().save_fixtures_to_db(
            fixtures_pack=PACK, fixtures_dict=FIXTURES_1
        )
        config.parse_args()

    def test_full_range_hash_partitioner(self):
        partitioner = HashPartitioner("node1", "MIN..MAX")
        sensors = partitioner.get_sensors()
        self.assertEqual(len(sensors), 3, "Expected all sensors")

    def test_multi_range_hash_partitioner(self):
        range_third = int(Range.RANGE_MAX_VALUE / 3)
        range_two_third = range_third * 2
        hash_ranges = "MIN..{range_third}|{range_third}..{range_two_third}|{range_two_third}..MAX".format(
            range_third=range_third, range_two_third=range_two_third
        )
        partitioner = HashPartitioner("node1", hash_ranges)
        sensors = partitioner.get_sensors()
        self.assertEqual(len(sensors), 3, "Expected all sensors")

    def test_split_range_hash_partitioner(self):
        range_mid = int(Range.RANGE_MAX_VALUE / 2)
        partitioner = HashPartitioner("node1", "MIN..%s" % range_mid)
        sensors1 = partitioner.get_sensors()

        partitioner = HashPartitioner("node2", "%s..MAX" % range_mid)
        sensors2 = partitioner.get_sensors()

        self.assertEqual(len(sensors1) + len(sensors2), 3, "Expected all sensors")

    def test_hash_effectiveness(self):
        range_third = int(Range.RANGE_MAX_VALUE / 3)
        partitioner1 = HashPartitioner("node1", "MIN..%s" % range_third)
        partitioner2 = HashPartitioner(
            "node2", "%s..%s" % (range_third, range_third + range_third)
        )
        partitioner3 = HashPartitioner("node2", "%s..MAX" % (range_third + range_third))

        refs_count = 1000

        refs = self._generate_refs(count=refs_count)

        p1_count = 0
        p2_count = 0
        p3_count = 0

        for ref in refs:
            if partitioner1._is_in_hash_range(ref):
                p1_count += 1
            # note if and not else-if.
            if partitioner2._is_in_hash_range(ref):
                p2_count += 1
            if partitioner3._is_in_hash_range(ref):
                p3_count += 1

        self.assertEqual(
            p1_count + p2_count + p3_count, refs_count, "Sum should equal all sensors."
        )

        # Test effectiveness by checking if the  sd is within 20% of mean
        mean = refs_count / 3
        variance = (
            float(
                (p1_count - mean) ** 2 + (p1_count - mean) ** 2 + (p3_count - mean) ** 2
            )
            / 3
        )
        sd = math.sqrt(variance)

        self.assertTrue(sd / mean <= 0.2, "Some values deviate too much from the mean.")

    def _generate_refs(self, count=10):
        random_word_count = int(math.sqrt(count)) + 1
        words = RandomWords().random_words(count=random_word_count)
        x_index = 0
        y_index = 0
        while count > 0:
            yield "%s.%s" % (words[x_index], words[y_index])
            if y_index < len(words) - 1:
                y_index += 1
            else:
                x_index += 1
                y_index = 0
            count -= 1
        return
