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
This module contains patched version of bencode function which knows how to handle unicode types.
"""

from __future__ import absolute_import

from types import UnicodeType

from mongoengine.base.datastructures import BaseDict

import bencode as bencode_upstream

__all__ = [
    'bencode',
    'bdecode'
]


def encode_unicode(x, r):
    x = x.encode('utf-8')
    r.extend((str(len(x)), ':', x))

# Patch bencode so it also knows how to encode unicode types
bencode_upstream.encode_func[UnicodeType] = encode_unicode
bencode_upstream.encode_func[BaseDict] = bencode_upstream.encode_dict


def bencode(x):
    return bencode_upstream.bencode(x)


def bdecode(x):
    return bencode_upstream.bdecode(x)
