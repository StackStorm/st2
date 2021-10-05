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
from st2common.util.enum import Enum

__all__ = ["ResourceType"]


class ResourceType(Enum):
    """
    Enum representing a valid resource type in a system.
    """

    # System resources
    RUNNER_TYPE = "runner_type"

    # Pack resources
    PACK = "pack"
    ACTION = "action"
    ACTION_ALIAS = "action_alias"
    SENSOR_TYPE = "sensor_type"
    TRIGGER_TYPE = "trigger_type"
    TRIGGER = "trigger"
    TRIGGER_INSTANCE = "trigger_instance"
    RULE = "rule"
    RULE_ENFORCEMENT = "rule_enforcement"

    # Note: Policy type is a global resource and policy belong to a pack
    POLICY_TYPE = "policy_type"
    POLICY = "policy"

    # Other resources
    EXECUTION = "execution"
    EXECUTION_REQUEST = "execution_request"
    KEY_VALUE_PAIR = "key_value_pair"

    WEBHOOK = "webhook"
    TIMER = "timer"
    API_KEY = "api_key"
    TRACE = "trace"
    TIMER = "timer"

    # Special resource type for stream related stuff
    STREAM = "stream"

    INQUIRY = "inquiry"

    UNKNOWN = "unknown"
