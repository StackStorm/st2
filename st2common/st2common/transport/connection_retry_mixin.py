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

"""
Mixin class for adding connection retry logic to Kombu ConsumerMixin classes.
"""

from __future__ import absolute_import

from oslo_config import cfg

from st2common import log as logging

__all__ = ["ConnectionRetryMixin"]

LOG = logging.getLogger(__name__)


class ConnectionRetryMixin(object):
    """
    Mixin that adds connection retry logic with configurable max attempts.

    This mixin prevents infinite retry loops when the message broker is unavailable
    by enforcing the max_retries configuration from messaging.connection_retry_max_attempts.

    Classes using this mixin should be combined with kombu.mixins.ConsumerMixin.

    The ConsumerMixin.run() method has built-in retry logic that calls on_connection_error()
    when connection fails, but by default it retries infinitely. This mixin overrides
    on_connection_error() to stop after max_retries attempts.

    Example:
        class MyConsumer(ConsumerMixin, ConnectionRetryMixin):
            def __init__(self, connection):
                self.connection = connection
                self._init_connection_retry()
    """

    def _init_connection_retry(self):
        """Initialize connection retry tracking. Call this in your __init__ method."""
        self._connection_retry_count = 0
        self._max_connection_retries = cfg.CONF.messaging.connection_retry_max_attempts

    def on_connection_error(self, exc, interval):
        """
        Override ConsumerMixin's connection error handler to enforce max retries.

        This prevents infinite retry loops when the broker is unavailable.
        After max_retries attempts, we raise the exception to kill the consumer.

        :param exc: The connection exception that occurred
        :param interval: Time in seconds before next retry attempt
        """
        self._connection_retry_count += 1

        if (
            self._max_connection_retries > 0
            and self._connection_retry_count >= self._max_connection_retries
        ):
            LOG.error(
                "Failed to connect to message broker after %d attempts. "
                "Giving up. Error: %s",
                self._connection_retry_count,
                exc,
            )
            # Raise the exception to stop the consumer
            raise exc

        max_retries_display = (
            self._max_connection_retries if self._max_connection_retries > 0 else "∞"
        )
        LOG.warning(
            "Broker connection error (attempt %d/%s), "
            "trying again in %.1f seconds: %s",
            self._connection_retry_count,
            max_retries_display,
            interval,
            exc,
        )

    def on_connection_revived(self):
        """
        Reset retry counter when connection is successfully re-established.
        """
        if self._connection_retry_count > 0:
            LOG.info(
                "Connection to message broker successfully re-established "
                "after %d attempts",
                self._connection_retry_count,
            )
        self._connection_retry_count = 0
