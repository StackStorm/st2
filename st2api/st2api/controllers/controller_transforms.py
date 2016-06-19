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
    'transform_to_bool'
]


def transform_to_bool(value):
    """
    Transforms a certain set of values to True or False.
    True can be represented by '1', 'True' and 'true.'
    False can be represented by '1', 'False' and 'false.'

    Any other representation will be rejected.
    """
    if value in ['1', 'true', 'True']:
        return True
    elif value in ['0', 'false', 'False']:
        return False
    raise ValueError('Invalid bool representation "%s" provided.' % value)
