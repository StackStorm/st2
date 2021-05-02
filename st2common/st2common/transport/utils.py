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

from __future__ import absolute_import

import ssl as ssl_lib

from oslo_config import cfg
from kombu import Connection

from st2common import log as logging

__all__ = ["get_connection", "get_messaging_urls"]

LOG = logging.getLogger(__name__)


def get_messaging_urls():
    """
    Determines the right messaging urls to supply. In case the `cluster_urls` config is
    specified then that is used. Else the single `url` property is used.

    :rtype: ``list``
    """
    if cfg.CONF.messaging.cluster_urls:
        return cfg.CONF.messaging.cluster_urls
    return [cfg.CONF.messaging.url]


def get_connection(urls=None, connection_kwargs=None):
    """
    Retrieve kombu "Conection" class instance configured with all the correct
    options using values from the config and provided values.

    :param connection_kwargs: Any additional connection keyword arguments passed directly to the
                              Connection class constructor.
    :type connection_kwargs: ``dict``
    """
    urls = urls or get_messaging_urls()
    connection_kwargs = connection_kwargs or {}

    kwargs = {}

    ssl_kwargs = _get_ssl_kwargs(
        ssl=cfg.CONF.messaging.ssl,
        ssl_keyfile=cfg.CONF.messaging.ssl_keyfile,
        ssl_certfile=cfg.CONF.messaging.ssl_certfile,
        ssl_cert_reqs=cfg.CONF.messaging.ssl_cert_reqs,
        ssl_ca_certs=cfg.CONF.messaging.ssl_ca_certs,
        login_method=cfg.CONF.messaging.login_method,
    )

    # NOTE: "connection_kwargs" argument passed to this function has precedence over config values
    if len(ssl_kwargs) == 1 and ssl_kwargs["ssl"] is True:
        kwargs.update({"ssl": True})
    elif len(ssl_kwargs) >= 2:
        ssl_kwargs.pop("ssl")
        kwargs.update({"ssl": ssl_kwargs})

    kwargs["login_method"] = cfg.CONF.messaging.login_method

    kwargs.update(connection_kwargs)

    # NOTE: This line contains no secret values so it's OK to log it
    LOG.debug("Using SSL context for RabbitMQ connection: %s" % (ssl_kwargs))

    connection = Connection(urls, **kwargs)
    return connection


def _get_ssl_kwargs(
    ssl=False,
    ssl_keyfile=None,
    ssl_certfile=None,
    ssl_cert_reqs=None,
    ssl_ca_certs=None,
    login_method=None,
):
    """
    Return SSL keyword arguments to be used with the kombu.Connection class.
    """
    ssl_kwargs = {}

    # NOTE: If "ssl" is not set to True we don't pass "ssl=False" argument to the constructor
    # because user could still specify to use SSL by including "?ssl=true" query param at the
    # end of the connection URL string
    if ssl is True:
        ssl_kwargs["ssl"] = True

    if ssl_keyfile:
        ssl_kwargs["ssl"] = True
        ssl_kwargs["keyfile"] = ssl_keyfile

    if ssl_certfile:
        ssl_kwargs["ssl"] = True
        ssl_kwargs["certfile"] = ssl_certfile

    if ssl_cert_reqs:
        if ssl_cert_reqs == "none":
            ssl_cert_reqs = ssl_lib.CERT_NONE
        elif ssl_cert_reqs == "optional":
            ssl_cert_reqs = ssl_lib.CERT_OPTIONAL
        elif ssl_cert_reqs == "required":
            ssl_cert_reqs = ssl_lib.CERT_REQUIRED
        ssl_kwargs["cert_reqs"] = ssl_cert_reqs

    if ssl_ca_certs:
        ssl_kwargs["ssl"] = True
        ssl_kwargs["ca_certs"] = ssl_ca_certs

    return ssl_kwargs
