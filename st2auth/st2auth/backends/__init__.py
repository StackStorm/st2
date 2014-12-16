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

import json

from oslo.config import cfg

from st2auth.backends.file import FileAuthenticationBackend

__all__ = [
    'get_backend_instance',
    'VALID_BACKEND_NAMES'
]

VALID_BACKEND_NAMES = [
    'file'
]


def get_backend_instance(name):
    """
    :param name: Backend name.
    :type name: ``str``
    """
    if name not in VALID_BACKEND_NAMES:
        raise ValueError('Invalid authentication backend specified: %s', name)

    if name == 'file':
        cls = FileAuthenticationBackend

    backend_kwargs = cfg.CONF.auth.backend_kwargs

    if backend_kwargs:
        kwargs = json.loads(backend_kwargs)
    else:
        kwargs = {}

    return cls(**kwargs)
