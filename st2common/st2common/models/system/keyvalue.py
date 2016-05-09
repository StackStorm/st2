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

from st2common.constants.keyvalue import PREFIX_SEPARATOR


class KeyReference(object):
    """
    Holds a reference to key given name and prefix. For example, if key name is foo and prefix
    is bob, this returns a string of form "bob.foo". This assumes '.' is the PREFIX_SEPARATOR.
    """

    def __init__(self, name, prefix=''):
        self._prefix = prefix
        self._name = name
        self.ref = ('%s%s%s' % (self._prefix, PREFIX_SEPARATOR, self._name)
                    if self._prefix else self._name)

    def __str__(self):
        return self.ref
