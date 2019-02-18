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

from __future__ import absolute_import

import os
import ssl
import socket

import unittest2
from oslo_config import cfg

from st2common.transport import utils as transport_utils

from st2tests.fixturesloader import get_fixtures_base_path

__all__ = [
    'RabbitMQTLSListenerTestCase'
]

CERTS_FIXTURES_PATH = os.path.join(get_fixtures_base_path(), 'ssl_certs/')
ON_TRAVIS = (os.environ.get('TRAVIS', 'false').lower() == 'true')

NON_SSL_LISTENER_PORT = 5672
SSL_LISTENER_PORT = 5671


# NOTE: We only run those tests on Travis because at the moment, local vagrant dev VM doesn't
# expose RabbitMQ SSL listener by default
# TODO: Re-enable once we upgrade Travis from Precise to Xenial where latest version of RabbitMQ
# and OpenSSL is available
@unittest2.skip('Skipping until we upgrade to Xenial on Travis')
# @unittest2.skipIf(not ON_TRAVIS, 'Skipping tests because not running on Travis')
class RabbitMQTLSListenerTestCase(unittest2.TestCase):

    def setUp(self):
        # Set default values
        cfg.CONF.set_override(name='ssl', override=False, group='messaging')
        cfg.CONF.set_override(name='ssl_keyfile', override=None, group='messaging')
        cfg.CONF.set_override(name='ssl_certfile', override=None, group='messaging')
        cfg.CONF.set_override(name='ssl_ca_certs', override=None, group='messaging')
        cfg.CONF.set_override(name='ssl_cert_reqs', override=None, group='messaging')

    def test_non_ssl_connection_on_ssl_listener_port_failure(self):
        connection = transport_utils.get_connection(urls='amqp://guest:guest@127.0.0.1:5671/')

        expected_msg_1 = '[Errno 104] Connection reset by peer'
        expected_msg_2 = 'Socket closed'

        try:
            connection.connect()
        except Exception as e:
            self.assertFalse(connection.connected)
            self.assertTrue(isinstance(e, (IOError, socket.error)))
            self.assertTrue(expected_msg_1 in str(e) or expected_msg_2 in str(e))
        else:
            self.fail('Exception was not thrown')

            if connection:
                connection.release()

    def test_ssl_connection_on_ssl_listener_success(self):
        # Using query param notation
        urls = 'amqp://guest:guest@127.0.0.1:5671/?ssl=true'
        connection = transport_utils.get_connection(urls=urls)

        try:
            self.assertTrue(connection.connect())
            self.assertTrue(connection.connected)
        finally:
            if connection:
                connection.release()

        # Using messaging.ssl config option
        cfg.CONF.set_override(name='ssl', override=True, group='messaging')

        connection = transport_utils.get_connection(urls='amqp://guest:guest@127.0.0.1:5671/')

        try:
            self.assertTrue(connection.connect())
            self.assertTrue(connection.connected)
        finally:
            if connection:
                connection.release()

    def test_ssl_connection_ca_certs_provided(self):
        ca_cert_path = os.path.join(CERTS_FIXTURES_PATH, 'ca/ca_certificate_bundle.pem')

        cfg.CONF.set_override(name='ssl', override=True, group='messaging')
        cfg.CONF.set_override(name='ssl_ca_certs', override=ca_cert_path, group='messaging')

        # 1. Validate server cert against a valid CA bundle (success) - cert required
        cfg.CONF.set_override(name='ssl_cert_reqs', override='required', group='messaging')

        connection = transport_utils.get_connection(urls='amqp://guest:guest@127.0.0.1:5671/')

        try:
            self.assertTrue(connection.connect())
            self.assertTrue(connection.connected)
        finally:
            if connection:
                connection.release()

        # 2. Validate server cert against other CA bundle (failure)
        # CA bundle which was not used to sign the server cert
        ca_cert_path = os.path.join('/etc/ssl/certs/thawte_Primary_Root_CA.pem')

        cfg.CONF.set_override(name='ssl_cert_reqs', override='required', group='messaging')
        cfg.CONF.set_override(name='ssl_ca_certs', override=ca_cert_path, group='messaging')

        connection = transport_utils.get_connection(urls='amqp://guest:guest@127.0.0.1:5671/')

        expected_msg = r'\[SSL: CERTIFICATE_VERIFY_FAILED\] certificate verify failed'
        self.assertRaisesRegexp(ssl.SSLError, expected_msg, connection.connect)

        # 3. Validate server cert against other CA bundle (failure)
        ca_cert_path = os.path.join('/etc/ssl/certs/thawte_Primary_Root_CA.pem')

        cfg.CONF.set_override(name='ssl_cert_reqs', override='optional', group='messaging')
        cfg.CONF.set_override(name='ssl_ca_certs', override=ca_cert_path, group='messaging')

        connection = transport_utils.get_connection(urls='amqp://guest:guest@127.0.0.1:5671/')

        expected_msg = r'\[SSL: CERTIFICATE_VERIFY_FAILED\] certificate verify failed'
        self.assertRaisesRegexp(ssl.SSLError, expected_msg, connection.connect)

        # 4. Validate server cert against other CA bundle (failure)
        # We use invalid bundle but cert_reqs is none
        ca_cert_path = os.path.join('/etc/ssl/certs/thawte_Primary_Root_CA.pem')

        cfg.CONF.set_override(name='ssl_cert_reqs', override='none', group='messaging')
        cfg.CONF.set_override(name='ssl_ca_certs', override=ca_cert_path, group='messaging')

        connection = transport_utils.get_connection(urls='amqp://guest:guest@127.0.0.1:5671/')

        try:
            self.assertTrue(connection.connect())
            self.assertTrue(connection.connected)
        finally:
            if connection:
                connection.release()

    def test_ssl_connect_client_side_cert_authentication(self):
        # 1. Success, valid client side cert provided
        ssl_keyfile = os.path.join(CERTS_FIXTURES_PATH, 'client/private_key.pem')
        ssl_certfile = os.path.join(CERTS_FIXTURES_PATH, 'client/client_certificate.pem')
        ca_cert_path = os.path.join(CERTS_FIXTURES_PATH, 'ca/ca_certificate_bundle.pem')

        cfg.CONF.set_override(name='ssl_keyfile', override=ssl_keyfile, group='messaging')
        cfg.CONF.set_override(name='ssl_certfile', override=ssl_certfile, group='messaging')
        cfg.CONF.set_override(name='ssl_cert_reqs', override='required', group='messaging')
        cfg.CONF.set_override(name='ssl_ca_certs', override=ca_cert_path, group='messaging')

        connection = transport_utils.get_connection(urls='amqp://guest:guest@127.0.0.1:5671/')

        try:
            self.assertTrue(connection.connect())
            self.assertTrue(connection.connected)
        finally:
            if connection:
                connection.release()

        # 2. Invalid client side cert provided - failure
        ssl_keyfile = os.path.join(CERTS_FIXTURES_PATH, 'client/private_key.pem')
        ssl_certfile = os.path.join(CERTS_FIXTURES_PATH, 'server/server_certificate.pem')
        ca_cert_path = os.path.join(CERTS_FIXTURES_PATH, 'ca/ca_certificate_bundle.pem')

        cfg.CONF.set_override(name='ssl_keyfile', override=ssl_keyfile, group='messaging')
        cfg.CONF.set_override(name='ssl_certfile', override=ssl_certfile, group='messaging')
        cfg.CONF.set_override(name='ssl_cert_reqs', override='required', group='messaging')
        cfg.CONF.set_override(name='ssl_ca_certs', override=ca_cert_path, group='messaging')

        connection = transport_utils.get_connection(urls='amqp://guest:guest@127.0.0.1:5671/')

        expected_msg = r'\[X509: KEY_VALUES_MISMATCH\] key values mismatch'
        self.assertRaisesRegexp(ssl.SSLError, expected_msg, connection.connect)
