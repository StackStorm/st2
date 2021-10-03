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


class ClusterRetryContext(object):
    """
    Stores retry context for cluster retries. It makes certain assumptions
    on how cluster_size and retry should be determined.
    """

    def __init__(self, cluster_size):
        # No of nodes in a cluster
        self.cluster_size = cluster_size
        # No of times to retry in a cluster
        self.cluster_retry = 2
        # time to wait between retry in a cluster
        self.wait_between_cluster = 10

        # No of nodes attempted. Starts at 1 since the
        self._nodes_attempted = 1

    def test_should_stop(self, e=None):
        # Special workaround for "(504) CHANNEL_ERROR - second 'channel.open' seen" which happens
        # during tests on Travis and block and slown down the tests
        # NOTE: This error is not fatal during tests and we can simply switch to a next connection
        # without sleeping.
        if "second 'channel.open' seen" in six.text_type(e):
            return False, -1

        should_stop = True
        if self._nodes_attempted > self.cluster_size * self.cluster_retry:
            return should_stop, -1
        wait = 0
        should_stop = False
        if self._nodes_attempted % self.cluster_size == 0:
            wait = self.wait_between_cluster
        self._nodes_attempted += 1
        return should_stop, wait


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

    def __init__(self, cluster_size, logger, ensure_max_retries=3):
        self._retry_context = ClusterRetryContext(cluster_size=cluster_size)
        self._logger = logger
        # How many times to try to retrying establishing a connection in a place where we are
        # calling connection.ensure_connection
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
        should_stop = False
        channel = None
        while not should_stop:
            try:
                channel = connection.channel()
                wrapped_callback(connection=connection, channel=channel)
                should_stop = True
            except connection.connection_errors + connection.channel_errors as e:
                should_stop, wait = self._retry_context.test_should_stop(e)
                # reset channel to None to avoid any channel closing errors. At this point
                # in case of an exception there should be no channel but that is better to
                # guarantee.
                channel = None
                # All attempts to re-establish connections have failed. This error needs to
                # be notified so raise.
                if should_stop:
                    raise

                # -1, 0 and 1+ are handled properly by eventlet.sleep
                self._logger.debug(
                    "Received RabbitMQ server error, sleeping for %s seconds "
                    "before retrying: %s" % (wait, six.text_type(e))
                )
                concurrency.sleep(wait)

                connection.close()
                # ensure_connection will automatically switch to an alternate. Other connections
                # in the pool will be fixed independently. It would be nice to cut-over the
                # entire ConnectionPool simultaneously but that would require writing our own
                # ConnectionPool. If a server recovers it could happen that the same process
                # ends up talking to separate nodes in a cluster.

                def log_error_on_conn_failure(exc, interval):
                    self._logger.debug(
                        "Failed to re-establish connection to RabbitMQ server, "
                        "retrying in %s seconds: %s" % (interval, six.text_type(exc))
                    )

                try:
                    # NOTE: This function blocks and tries to restablish a connection for
                    # indefinetly if "max_retries" argument is not specified
                    connection.ensure_connection(
                        max_retries=self._ensure_max_retries,
                        errback=log_error_on_conn_failure,
                    )
                except Exception:
                    self._logger.exception(
                        "Connections to RabbitMQ cannot be re-established: %s",
                        six.text_type(e),
                    )
                    raise
            except Exception as e:
                self._logger.exception(
                    "Connections to RabbitMQ cannot be re-established: %s",
                    six.text_type(e),
                )
                # Not being able to publish a message could be a significant issue for an app.
                raise
            finally:
                if should_stop and channel:
                    try:
                        channel.close()
                    except Exception:
                        self._logger.warning("Error closing channel.", exc_info=True)

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
