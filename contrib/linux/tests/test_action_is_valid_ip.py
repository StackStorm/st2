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

from st2tests.base import BaseActionTestCase

from is_valid_ip import IsValidIp

__all__ = [
    'IsValidIpTestCase'
]


class IsValidIpTestCase(BaseActionTestCase):
    __test__ = True
    action_cls = IsValidIp

    def test_run_valid_ip_v4(self):
        expected = {'is_link_local': False,
                    'is_loopback': False,
                    'is_multicast': False,
                    'is_private': True,
                    'is_reserved': False,
                    'is_unspecified': False,
                    'reverse_pointer': '1.0.168.192.in-addr.arpa',
                    'version': 4}

        action = self.get_action_instance()

        result = action.run("192.168.0.1")
        self.assertEqual(result, expected)

    def test_run_valid_ip_v6(self):
        expected = {'is_link_local': False,
                    'is_loopback': False,
                    'is_multicast': False,
                    'is_private': False,
                    'is_reserved': True,
                    'is_unspecified': False,
                    'reverse_pointer': '8.1.f.a.1.0.0.0.3.0.b.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.2.6.7.1.ip6.arpa',
                    'version': 6}

        action = self.get_action_instance()
        result = action.run("1762:0:0:0:0:B03:1:AF18")
        self.assertEqual(result, expected)

    def test_run_invalid_ip_v6(self):
        action = self.get_action_instance()

        self.assertRaises(ValueError,
                          action.run,
                          "1762:%:0:0:0:B03:1:AF18")

    def test_run_ipv4_loopback_invalid_with_no_loopback(self):
        action = self.get_action_instance()

        self.assertRaises(ValueError,
                          action.run,
                          "127.0.0.1",
                          no_loopback=True)

    def test_run_ipv6_loopback_invalid_with_no_loopback(self):
        action = self.get_action_instance()

        self.assertRaises(ValueError,
                          action.run,
                          "::1",
                          no_loopback=True)

    def test_run_ipv4_valid_with_only_v4(self):
        expected = {'is_link_local': False,
                    'is_loopback': False,
                    'is_multicast': False,
                    'is_private': True,
                    'is_reserved': False,
                    'is_unspecified': False,
                    'reverse_pointer': '1.0.168.192.in-addr.arpa',
                    'version': 4}

        action = self.get_action_instance()
        result = action.run("192.168.0.1",
                            only_v4=True)
        self.assertEqual(result, expected)

    def test_run_ipv6_invalid_with_only_v4(self):
        action = self.get_action_instance()

        self.assertRaises(ValueError,
                          action.run,
                          "1762:0:0:0:0:B03:1:AF18",
                          only_v4=True)

    def test_run_ipv6_valid_with_only_v6(self):
        expected = {'is_link_local': False,
                    'is_loopback': False,
                    'is_multicast': False,
                    'is_private': False,
                    'is_reserved': True,
                    'is_unspecified': False,
                    'reverse_pointer': '8.1.f.a.1.0.0.0.3.0.b.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.2.6.7.1.ip6.arpa',
                    'version': 6}

        action = self.get_action_instance()
        result = action.run("1762:0:0:0:0:B03:1:AF18",
                            only_v6=True)
        self.assertEqual(result, expected)

    def test_run_ipv4_invalid_with_only_v6(self):
        action = self.get_action_instance()

        self.assertRaises(ValueError,
                          action.run,
                          "127.0.0.1",
                          only_v6=True)
