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

__all__ = [
    'MASKED_ATTRIBUTES_BLACKLIST',
    'MASKED_ATTRIBUTE_VALUE'
]

# A blacklist of attributes which should be masked in the log messages by default.
# Note: If an attribute is an object or a dict, we try to recursively process it and mask the
# values.
MASKED_ATTRIBUTES_BLACKLIST = [
    'password',
    'auth_token',
    'token',
    'secret',
    'credentials',
    'st2_auth_token'
]

# Value with which the masked attribute values are replaced
MASKED_ATTRIBUTE_VALUE = '********'
