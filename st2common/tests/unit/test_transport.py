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

import ssl

import unittest2

from st2common.transport.utils import _get_ssl_kwargs

__all__ = [
    'TransportUtilsTestCase'
]


class TransportUtilsTestCase(unittest2.TestCase):
    def test_get_ssl_kwargs(self):
        # 1. No SSL kwargs provided
        ssl_kwargs = _get_ssl_kwargs()
        self.assertEqual(ssl_kwargs, {})

        # 2. ssl kwarg provided
        ssl_kwargs = _get_ssl_kwargs(ssl=True)
        self.assertEqual(ssl_kwargs, {
            'ssl': True
        })

        # 3. ssl_keyfile provided
        ssl_kwargs = _get_ssl_kwargs(ssl_keyfile='/tmp/keyfile')
        self.assertEqual(ssl_kwargs, {
            'ssl': True,
            'keyfile': '/tmp/keyfile'
        })

        # 4. ssl_certfile provided
        ssl_kwargs = _get_ssl_kwargs(ssl_certfile='/tmp/certfile')
        self.assertEqual(ssl_kwargs, {
            'ssl': True,
            'certfile': '/tmp/certfile'
        })

        # 5. ssl_ca_certs provided
        ssl_kwargs = _get_ssl_kwargs(ssl_ca_certs='/tmp/ca_certs')
        self.assertEqual(ssl_kwargs, {
            'ssl': True,
            'ca_certs': '/tmp/ca_certs'
        })

        # 6. ssl_ca_certs and ssl_cert_reqs combinations
        ssl_kwargs = _get_ssl_kwargs(ssl_ca_certs='/tmp/ca_certs', ssl_cert_reqs='none')
        self.assertEqual(ssl_kwargs, {
            'ssl': True,
            'ca_certs': '/tmp/ca_certs',
            'cert_reqs': ssl.CERT_NONE
        })

        ssl_kwargs = _get_ssl_kwargs(ssl_ca_certs='/tmp/ca_certs', ssl_cert_reqs='optional')
        self.assertEqual(ssl_kwargs, {
            'ssl': True,
            'ca_certs': '/tmp/ca_certs',
            'cert_reqs': ssl.CERT_OPTIONAL
        })

        ssl_kwargs = _get_ssl_kwargs(ssl_ca_certs='/tmp/ca_certs', ssl_cert_reqs='required')
        self.assertEqual(ssl_kwargs, {
            'ssl': True,
            'ca_certs': '/tmp/ca_certs',
            'cert_reqs': ssl.CERT_REQUIRED
        })
