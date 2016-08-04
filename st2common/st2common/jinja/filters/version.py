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

import semver

__all__ = [
    'version_compare',
    'version_more_than',
    'version_less_than',
    'version_equal',
    'version_match',
    'version_bump_major',
    'version_bump_minor'
]


def version_compare(value, pattern):
    return semver.compare(value, pattern)


def version_more_than(value, pattern):
    return semver.compare(value, pattern) == 1


def version_less_than(value, pattern):
    return semver.compare(value, pattern) == -1


def version_equal(value, pattern):
    return semver.compare(value, pattern) == 0


def version_match(value, pattern):
    return semver.match(value, pattern)


def version_bump_major(value):
    return semver.bump_major(value)


def version_bump_minor(value):
    return semver.bump_minor(value)


def version_bump_patch(value):
    return semver.bump_patch(value)


def version_strip_patch(value):
    return "{major}.{minor}".format(**semver.parse(value))
