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
Common model related classes.
"""

__all__ = [
    'DictSerializableClassMixin'
]


class DictSerializableClassMixin(object):
    """
    Mixin class which is to be used with classes which can be serialized as a dictionary,
    """

    def mask_secrets(self, value):
        """
        Process the object and mask secret values.

        :type value: ``dict``
        :param value: Document dictionary.

        :rtype: ``dict``
        """
        return value

    def to_serializable_dict(self, mask_secrets=False):
        """
        Serialize object to a dictionary which can be serialized as JSON.

        :param mask_secrets: True to mask secrets in the resulting dict.
        :type mask_secrets: ``boolean``

        :rtype: ``dict``
        """
        raise NotImplementedError()
