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
import importlib

from oslo_config import cfg

from st2common.util.loader import _get_classes_in_module

__all__ = [
    'get_backend_instance',
    'VALID_BACKEND_NAMES'
]

BACKEND_MODULES = {
    'flat_file': 'st2auth.backends.flat_file',
    'ldap_backend': 'st2auth.backends.ldap_backend',
    'mongodb': 'st2auth.backends.mongodb'
}

VALID_BACKEND_NAMES = BACKEND_MODULES.keys()


def get_backend_instance(name):
    """
    :param name: Backend name.
    :type name: ``str``
    """
    if name not in VALID_BACKEND_NAMES:
        raise ValueError('Invalid authentication backend specified: %s', name)

    module = importlib.import_module(BACKEND_MODULES[name])
    classes = _get_classes_in_module(module=module)

    try:
        cls = [klass for klass in classes if klass.__name__.endswith('AuthenticationBackend')][0]
    except IndexError:
        raise ValueError('"%s" backend module doesn\'t export a compatible class' % (name))

    backend_kwargs = cfg.CONF.auth.backend_kwargs

    if backend_kwargs:
        try:
            kwargs = json.loads(backend_kwargs)
        except ValueError:
            raise ValueError('Failed to JSON parse backend settings')
    else:
        kwargs = {}

    return cls(**kwargs)
