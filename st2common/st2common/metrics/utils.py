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

import six
from oslo_config import cfg

__all__ = ["get_full_key_name", "check_key"]


def get_full_key_name(key):
    """
    Return full metric key name, taking into account optional  prefix which can be specified in the
    config.
    """
    parts = ["st2"]

    if cfg.CONF.metrics.prefix:
        parts.append(cfg.CONF.metrics.prefix)

    parts.append(key)

    return ".".join(parts)


def check_key(key):
    """
    Ensure key meets requirements.
    """
    assert isinstance(key, six.string_types), "Key not a string. Got %s" % type(key)
    assert key, "Key cannot be empty string."
