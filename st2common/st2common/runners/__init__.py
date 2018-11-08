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

# Note: Imports are in-line to avoid large import time overhead

from __future__ import absolute_import

__all__ = [
    'BACKENDS_NAMESPACE',

    'get_available_backends',
    'get_backend_instance'
]

BACKENDS_NAMESPACE = 'st2common.runners.runner'


def get_available_backends():
    """
    Return names of the available / installed action runners.

    :rtype: ``list`` of ``str``
    """
    from stevedore.extension import ExtensionManager

    manager = ExtensionManager(namespace=BACKENDS_NAMESPACE, invoke_on_load=False)
    return manager.names()


def get_backend_instance(name):
    """
    Return a class instance for the provided runner name.
    """
    from stevedore.driver import DriverManager

    manager = DriverManager(namespace=BACKENDS_NAMESPACE, name=name, invoke_on_load=False)
    return manager.driver
