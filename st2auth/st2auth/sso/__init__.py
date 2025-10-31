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

import json
import six
import traceback

from oslo_config import cfg

from st2common import log as logging

from st2common.util import driver_loader


__all__ = ["get_available_backends", "get_backend_instance", "get_sso_backend"]

LOG = logging.getLogger(__name__)

BACKENDS_NAMESPACE = "st2auth.sso.backends"  # pants: no-infer-dep


def get_available_backends():
    return driver_loader.get_available_backends(namespace=BACKENDS_NAMESPACE)


def get_backend_instance(name):
    sso_backend_cls = driver_loader.get_backend_driver(
        namespace=BACKENDS_NAMESPACE, name=name
    )

    kwargs = {}
    sso_backend_kwargs = cfg.CONF.auth.sso_backend_kwargs

    if sso_backend_kwargs:
        try:
            kwargs = json.loads(sso_backend_kwargs)
        except ValueError as e:
            raise ValueError(
                'Failed to JSON parse backend settings for backend "%s": %s'
                % (name, six.text_type(e))
            )

    try:
        sso_backend = sso_backend_cls(**kwargs)
    except Exception as e:
        tb_msg = traceback.format_exc()
        class_name = sso_backend_cls.__name__
        msg = (
            'Failed to instantiate SSO backend "%s" (class %s) with backend settings '
            '"%s": %s' % (name, class_name, str(kwargs), six.text_type(e))
        )
        msg += "\n\n" + tb_msg
        exc_cls = type(e)
        raise exc_cls(msg)

    return sso_backend


def get_sso_backend():
    """
    Return SingleSignOnBackend class instance.
    """
    return get_backend_instance(cfg.CONF.auth.sso_backend)
