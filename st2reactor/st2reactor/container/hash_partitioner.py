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

import ctypes
import hashlib

from st2reactor.container.partitioners import DefaultPartitioner, get_all_enabled_sensors

__all__ = [
    'HashPartitioner',
    'Range'
]

# The range expression serialized is of the form `RANGE_START..RANGE_END|RANGE_START..RANGE_END ...`
SUB_RANGE_SEPARATOR = '|'
RANGE_BOUNDARY_SEPARATOR = '..'


class Range(object):

    RANGE_MIN_ENUM = 'min'
    RANGE_MIN_VALUE = 0

    RANGE_MAX_ENUM = 'max'
    RANGE_MAX_VALUE = 2**32

    def __init__(self, range_repr):
        self.range_start, self.range_end = self._get_range_boundaries(range_repr)

    def __contains__(self, item):
        return item >= self.range_start and item < self.range_end

    def _get_range_boundaries(self, range_repr):
        range_repr = [value.strip() for value in range_repr.split(RANGE_BOUNDARY_SEPARATOR)]
        if len(range_repr) != 2:
            raise ValueError('Unsupported sub-range format %s.' % range_repr)

        range_start = self._get_valid_range_boundary(range_repr[0])
        range_end = self._get_valid_range_boundary(range_repr[1])

        if range_start > range_end:
            raise ValueError('Misconfigured range [%d..%d]' % (range_start, range_end))
        return (range_start, range_end)

    def _get_valid_range_boundary(self, boundary_value):
        # Not elegant by any means but super clear.
        if boundary_value.lower() == self.RANGE_MIN_ENUM:
            return self.RANGE_MIN_VALUE
        if boundary_value.lower() == self.RANGE_MAX_ENUM:
            return self.RANGE_MAX_VALUE
        boundary_value = int(boundary_value)
        # Disallow any value less than the RANGE_MIN_VALUE or more than RANGE_MAX_VALUE.
        # Decided against raising a ValueError as it is manageable. Should not lead to
        # unexpected behavior.
        if boundary_value < self.RANGE_MIN_VALUE:
            return self.RANGE_MIN_VALUE
        if boundary_value > self.RANGE_MAX_VALUE:
            return self.RANGE_MAX_VALUE
        return boundary_value


class HashPartitioner(DefaultPartitioner):

    def __init__(self, sensor_node_name, hash_ranges):
        super(HashPartitioner, self).__init__(sensor_node_name=sensor_node_name)
        self._hash_ranges = self._create_hash_ranges(hash_ranges)

    def is_sensor_owner(self, sensor_db):
        return self._is_in_hash_range(sensor_db.get_reference().ref)

    def get_sensors(self):
        all_enabled_sensors = get_all_enabled_sensors()

        partition_members = []

        for sensor in all_enabled_sensors:
            sensor_ref = sensor.get_reference()
            if self._is_in_hash_range(sensor_ref.ref):
                partition_members.append(sensor)

        return partition_members

    def _is_in_hash_range(self, sensor_ref):
        sensor_ref_hash = self._hash_sensor_ref(sensor_ref)
        for hash_range in self._hash_ranges:
            if sensor_ref_hash in hash_range:
                return True
        return False

    def _hash_sensor_ref(self, sensor_ref):
        # Hmm... maybe this should be done in C. If it becomes a performance
        # bottleneck will look at that optimization.

        # From http://www.cs.hmc.edu/~geoff/classes/hmc.cs070.200101/homework10/hashfuncs.html
        # The 'liberal' use of ctypes.c_unit is to guarantee unsigned integer and workaround
        # inifinite precision.
        md5_hash = hashlib.md5(sensor_ref.encode())
        md5_hash_int_repr = int(md5_hash.hexdigest(), 16)
        h = ctypes.c_uint(0)
        for d in reversed(str(md5_hash_int_repr)):
            d = ctypes.c_uint(int(d))
            higherorder = ctypes.c_uint(h.value & 0xf8000000)
            h = ctypes.c_uint(h.value << 5)
            h = ctypes.c_uint(h.value ^ (higherorder.value >> 27))
            h = ctypes.c_uint(h.value ^ d.value)
        return h.value

    def _create_hash_ranges(self, hash_ranges_repr):
        """
        Extract from a format like - 0..1024|2048..4096|4096..MAX
        """
        hash_ranges = []
        # Likely all this splitting can be avoided and done nicely with regex but I generally
        # dislike using regex so I go with naive approaches.
        for range_repr in hash_ranges_repr.split(SUB_RANGE_SEPARATOR):
            hash_range = Range(range_repr.strip())
            hash_ranges.append(hash_range)
        return hash_ranges
