# Licensed to the Apache Software Foundation (ASF) under one or more
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

import unittest2

from st2common.util.ip_utils import split_host_port


class IPUtilsTests(unittest2.TestCase):

    def test_host_port_split(self):

        # Simple IPv4
        host_str = '1.2.3.4'
        host, port = split_host_port(host_str)
        self.assertEqual(host, host_str)
        self.assertEqual(port, None)

        # Simple IPv4 with port
        host_str = '1.2.3.4:55'
        host, port = split_host_port(host_str)
        self.assertEqual(host, '1.2.3.4')
        self.assertEqual(port, 55)

        # Simple IPv6
        host_str = 'fec2::10'
        host, port = split_host_port(host_str)
        self.assertEqual(host, 'fec2::10')
        self.assertEqual(port, None)

        # IPv6 with square brackets no port
        host_str = '[fec2::10]'
        host, port = split_host_port(host_str)
        self.assertEqual(host, 'fec2::10')
        self.assertEqual(port, None)

        # IPv6 with square brackets with port
        host_str = '[fec2::10]:55'
        host, port = split_host_port(host_str)
        self.assertEqual(host, 'fec2::10')
        self.assertEqual(port, 55)

        # IPv4 inside bracket
        host_str = '[1.2.3.4]'
        host, port = split_host_port(host_str)
        self.assertEqual(host, '1.2.3.4')
        self.assertEqual(port, None)

        # IPv4 inside bracket and port
        host_str = '[1.2.3.4]:55'
        host, port = split_host_port(host_str)
        self.assertEqual(host, '1.2.3.4')
        self.assertEqual(port, 55)

        # Hostname inside bracket
        host_str = '[st2build001]:55'
        host, port = split_host_port(host_str)
        self.assertEqual(host, 'st2build001')
        self.assertEqual(port, 55)

        # Simple hostname
        host_str = 'st2build001'
        host, port = split_host_port(host_str)
        self.assertEqual(host, 'st2build001')
        self.assertEqual(port, None)

        # Simple hostname with port
        host_str = 'st2build001:55'
        host, port = split_host_port(host_str)
        self.assertEqual(host, 'st2build001')
        self.assertEqual(port, 55)

        # No-bracket invalid port
        host_str = 'st2build001:abc'
        self.assertRaises(Exception, split_host_port, host_str)

        # Bracket invalid port
        host_str = '[fec2::10]:abc'
        self.assertRaises(Exception, split_host_port, host_str)
