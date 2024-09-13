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
import semver

__all__ = [
    "version_compare",
    "version_more_than",
    "version_less_than",
    "version_equal",
    "version_match",
    "version_bump_major",
    "version_bump_minor",
]


def version_compare(value, pattern):
    return semver.Version.parse(value).compare(pattern)


def version_more_than(value, pattern):
    return version_compare(value, pattern) == 1


def version_less_than(value, pattern):
    return version_compare(value, pattern) == -1


def version_equal(value, pattern):
    return version_compare(value, pattern) == 0


def version_match(value, pattern):
    return semver.Version.parse(value).match(pattern)


def version_bump_major(value):
    return str(semver.Version.parse(value).bump_major())


def version_bump_minor(value):
    return str(semver.Version.parse(value).bump_minor())


def version_bump_patch(value):
    return str(semver.Version.parse(value).bump_patch())


def version_strip_patch(value):
    sv = semver.Version.parse(value)
    return f"{sv.major}.{sv.minor}"
