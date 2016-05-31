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

import ipaddress

from st2actions.runners.pythonrunner import Action


class IsValidIpAction(Action):
    def run(self, ip_address, no_loopback=False, only_v4=False, only_v6=False):
        """
        Is this a valid IP address?

        Args:
          ip_address: The IP address to validate.
          no_loopback: Raise an exception for Loopback addresses.
          only_v4: Raise an exception for IPv6 addresses.
          only_v6: Raise an exception for IPv4 addresses.

        Raises:
          ValueError: On invalid IP, loopback or when requesting only v4/v6
                      be considered valid.

        Returns:
          dict: With extra information about the IP address.
        """

        # As ipaddress is a backport from Python 3.3+ it errors if the
        # ip address is a string and not unicode.
        ip_obj = ipaddress.ip_address(unicode(ip_address))

        results = {'version': ip_obj.version,
                   'is_private': ip_obj.is_private,
                   'is_link_local': ip_obj.is_link_local,
                   'is_unspecified': ip_obj.is_unspecified,
                   'reverse_pointer': ip_obj.reverse_pointer,
                   'is_multicast': ip_obj.is_multicast,
                   'is_reserved': ip_obj.is_reserved,
                   'is_loopback': ip_obj.is_loopback}

        if only_v6 and ip_obj.version == 4:
            raise ValueError("Valid IPv4 address, but IPv6 is required.")
        elif only_v4 and ip_obj.version == 6:
            raise ValueError("Valid IPv6 address, but IPv4 is required.")

        if no_loopback and ip_obj.is_loopback:
            raise ValueError("Address is a IPv{} loopback address".format(
                ip_obj.version))

        return results
