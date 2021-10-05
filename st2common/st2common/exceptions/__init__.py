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


class StackStormBaseException(Exception):
    """
    The root of the exception class hierarchy for all
    StackStorm server exceptions.

    For exceptions raised by plug-ins, see StackStormPluginException
    class.
    """

    pass


class StackStormPluginException(StackStormBaseException):
    """
    The root of the exception class hierarchy for all
    exceptions that are defined as part of a StackStorm
    plug-in API.

    It is recommended that each API define a root exception
    class for the API. This root exception class for the
    API should inherit from the StackStormPluginException
    class.
    """

    pass
