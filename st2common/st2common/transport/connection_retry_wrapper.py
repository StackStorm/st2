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

import six

from st2common.util import concurrency

__all__ = ["ConnectionRetryWrapper", "ClusterRetryContext"]

# Higher-level exception tuple that covers all connection-related errors


class ClusterRetryContext(object):
    """
    Stores retry context for cluster retries.
    """

    def __init__(self, cluster_size, max_retries=2, wait_between_retry=10):
        self.cluster_size = cluster_size
        self.max_retries = max_retries
        self.wait_between_retry = wait_between_retry
        self._attempt_count = 0
        self._max_attempts = cluster_size * (max_retries + 1)

    def should_stop(self, e=None):
        """
        Determine if retry should stop and how long to wait before next attempt.

        Returns:
            tuple: (should_stop, wait_seconds)
        """
        self._attempt_count += 1

        # Special workaround for non-fatal test errors
        if "second 'channel.open' seen" in six.text_type(e):
            return False, 0

        if self._attempt_count >= self._max_attempts:
            return True, 0

        # Wait before retrying after cycling through all cluster nodes
        wait = (
            self.wait_between_retry
            if self._attempt_count % self.cluster_size == 0
            else 0
        )
        return False, wait


class ConnectionRetryWrapper(object):
    """
    Manages retry of connection and also switching to different nodes in a cluster.

    :param cluster_size: Size of the cluster.
    :param logger: logger to use to log moderately useful information.

    .. code-block:: python
        # Without ensuring recoverable errors are retried
        connection_urls = [
            'amqp://guest:guest@node1:5672',
            'amqp://guest:guest@node2:5672',
            'amqp://guest:guest@node3:5672'
        ]
        with Connection(connection_urls) as connection:
            retry_wrapper = ConnectionRetryWrapper(cluster_size=len(connection_urls),
                                                   logger=my_logger)
            # wrapped_callback must have signature ``def func(connection, channel)``
            def wrapped_callback(connection, channel):
                pass

            retry_wrapper.run(connection=connection, wrapped_callback=wrapped_callback)

        # With ensuring recoverable errors are retried
        connection_urls = [
            'amqp://guest:guest@node1:5672',
            'amqp://guest:guest@node2:5672',
            'amqp://guest:guest@node3:5672'
        ]
        with Connection(connection_urls) as connection:
            retry_wrapper = ConnectionRetryWrapper(cluster_size=len(connection_urls),
                                                   logger=my_logger)
            # wrapped_callback must have signature ``def func(connection, channel)``
            def wrapped_callback(connection, channel):
                kwargs = {...}
                # call ensured to correctly deal with recoverable errors.
                retry_wrapper.ensured(connection=connection_retry_wrapper,
                                      obj=my_obj,
                                      to_ensure_func=my_obj.ensuree,
                                      **kwargs)

            retry_wrapper.run(connection=connection, wrapped_callback=wrapped_callback)

    """

    def __init__(self, cluster_size, logger, max_retries=2, ensure_max_retries=3):
        self._retry_context = ClusterRetryContext(
            cluster_size=cluster_size, max_retries=max_retries
        )
        self._logger = logger
        self._ensure_max_retries = ensure_max_retries

    def errback(self, exc, interval):
        self._logger.error("Rabbitmq connection error: %s", exc.message)

    def run(self, connection, wrapped_callback):
        """
        Run the wrapped_callback in a protective covering of retries and error handling.

        :param connection: Connection to messaging service
        :type connection: kombu.connection.Connection

        :param wrapped_callback: Callback that will be wrapped by all the fine handling in this
                                 method. Expected signature of callback -
                                 ``def func(connection, channel)``
        """
        channel = None
        while True:
            try:
                channel = connection.channel()
                wrapped_callback(connection=connection, channel=channel)
                break  # Success - exit the retry loop
            except Exception as e:
                channel = None  # Reset channel to avoid closing errors
                should_stop, wait = self._retry_context.should_stop(e)

                if should_stop:
                    self._logger.error(
                        "Failed to execute operation after exhausting all retry attempts"
                    )
                    raise

                if wait > 0:
                    self._logger.debug(
                        "Received RabbitMQ server error, sleeping for %s seconds "
                        "before retrying: %s" % (wait, six.text_type(e))
                    )
                    concurrency.sleep(wait)

                connection.close()

                # ensure_connection will automatically switch to an alternate node
                def log_error_on_conn_failure(exc, interval):
                    self._logger.debug(
                        "Failed to re-establish connection to RabbitMQ server, "
                        "retrying in %s seconds: %s" % (interval, six.text_type(exc))
                    )

                try:
                    connection.ensure_connection(
                        max_retries=self._ensure_max_retries,
                        errback=log_error_on_conn_failure,
                    )
                except Exception:
                    self._logger.error("Failed to re-establish connection to RabbitMQ")
                    raise
            finally:
                if channel:
                    channel.close()

    def ensured(self, connection, obj, to_ensure_func, **kwargs):
        """
        Ensure that recoverable errors are retried a set number of times before giving up.

        :param connection: Connection to messaging service
        :type connection: kombu.connection.Connection

        :param obj: Object whose method is to be ensured. Typically, channel, producer etc. from
                    the kombu library.
        :type obj: Must support mixin kombu.abstract.MaybeChannelBound
        """
        ensuring_func = connection.ensure(
            obj, to_ensure_func, errback=self.errback, max_retries=3
        )
        ensuring_func(**kwargs)
