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
import itertools

from st2common.util.enum import Enum
from st2common.constants.types import ResourceType as SystemResourceType

__all__ = [
    "SystemRole",
    "PermissionType",
    "ResourceType",
    "RESOURCE_TYPE_TO_PERMISSION_TYPES_MAP",
    "PERMISION_TYPE_TO_DESCRIPTION_MAP",
    "ALL_PERMISSION_TYPES",
    "GLOBAL_PERMISSION_TYPES",
    "GLOBAL_PACK_PERMISSION_TYPES",
    "LIST_PERMISSION_TYPES",
    "get_resource_permission_types_with_descriptions",
]


class PermissionType(Enum):
    """
    Available permission types.
    """

    # Note: There is no create endpoint for runner types right now
    RUNNER_LIST = "runner_type_list"
    RUNNER_VIEW = "runner_type_view"
    RUNNER_MODIFY = "runner_type_modify"
    RUNNER_ALL = "runner_type_all"

    PACK_LIST = "pack_list"
    PACK_VIEW = "pack_view"
    PACK_CREATE = "pack_create"
    PACK_MODIFY = "pack_modify"
    PACK_DELETE = "pack_delete"

    # Pack-management specific permissions
    # Note: Right now those permissions are global and apply to all the packs.
    # In the future we plan to support globs.
    PACK_INSTALL = "pack_install"
    PACK_UNINSTALL = "pack_uninstall"
    PACK_REGISTER = "pack_register"
    PACK_CONFIG = "pack_config"
    PACK_SEARCH = "pack_search"
    PACK_VIEWS_INDEX_HEALTH = "pack_views_index_health"

    PACK_ALL = "pack_all"

    # Note: Right now we only have read endpoints + update for sensors types
    SENSOR_LIST = "sensor_type_list"
    SENSOR_VIEW = "sensor_type_view"
    SENSOR_MODIFY = "sensor_type_modify"
    SENSOR_ALL = "sensor_type_all"

    ACTION_LIST = "action_list"
    ACTION_VIEW = "action_view"
    ACTION_CREATE = "action_create"
    ACTION_MODIFY = "action_modify"
    ACTION_DELETE = "action_delete"
    ACTION_EXECUTE = "action_execute"
    ACTION_ALL = "action_all"

    ACTION_ALIAS_LIST = "action_alias_list"
    ACTION_ALIAS_VIEW = "action_alias_view"
    ACTION_ALIAS_CREATE = "action_alias_create"
    ACTION_ALIAS_MODIFY = "action_alias_modify"
    ACTION_ALIAS_MATCH = "action_alias_match"
    ACTION_ALIAS_HELP = "action_alias_help"
    ACTION_ALIAS_DELETE = "action_alias_delete"
    ACTION_ALIAS_ALL = "action_alias_all"

    # Note: Execution create is granted with "action_execute"
    EXECUTION_LIST = "execution_list"
    EXECUTION_VIEW = "execution_view"
    EXECUTION_RE_RUN = "execution_rerun"
    EXECUTION_STOP = "execution_stop"
    EXECUTION_ALL = "execution_all"
    EXECUTION_VIEWS_FILTERS_LIST = "execution_views_filters_list"

    RULE_LIST = "rule_list"
    RULE_VIEW = "rule_view"
    RULE_CREATE = "rule_create"
    RULE_MODIFY = "rule_modify"
    RULE_DELETE = "rule_delete"
    RULE_ALL = "rule_all"

    RULE_ENFORCEMENT_LIST = "rule_enforcement_list"
    RULE_ENFORCEMENT_VIEW = "rule_enforcement_view"

    # TODO - Maybe "datastore_item" / key_value_item ?
    KEY_VALUE_PAIR_LIST = "key_value_pair_list"
    KEY_VALUE_PAIR_VIEW = "key_value_pair_view"
    KEY_VALUE_PAIR_SET = "key_value_pair_set"
    KEY_VALUE_PAIR_DELETE = "key_value_pair_delete"
    KEY_VALUE_PAIR_ALL = "key_value_pair_all"

    WEBHOOK_LIST = "webhook_list"
    WEBHOOK_VIEW = "webhook_view"
    WEBHOOK_CREATE = "webhook_create"
    WEBHOOK_SEND = "webhook_send"
    WEBHOOK_DELETE = "webhook_delete"
    WEBHOOK_ALL = "webhook_all"

    TIMER_LIST = "timer_list"
    TIMER_VIEW = "timer_view"
    TIMER_ALL = "timer_all"

    API_KEY_LIST = "api_key_list"
    API_KEY_VIEW = "api_key_view"
    API_KEY_CREATE = "api_key_create"
    API_KEY_MODIFY = "api_key_modify"
    API_KEY_DELETE = "api_key_delete"
    API_KEY_ALL = "api_key_all"

    TRACE_LIST = "trace_list"
    TRACE_VIEW = "trace_view"
    TRACE_ALL = "trace_all"

    # Note: Trigger permissions types are also used for Timer API endpoint since timer is just
    # a special type of a trigger
    TRIGGER_LIST = "trigger_list"
    TRIGGER_VIEW = "trigger_view"
    TRIGGER_ALL = "trigger_all"

    POLICY_TYPE_LIST = "policy_type_list"
    POLICY_TYPE_VIEW = "policy_type_view"
    POLICY_TYPE_ALL = "policy_type_all"

    POLICY_LIST = "policy_list"
    POLICY_VIEW = "policy_view"
    POLICY_CREATE = "policy_create"
    POLICY_MODIFY = "policy_modify"
    POLICY_DELETE = "policy_delete"
    POLICY_ALL = "policy_all"

    STREAM_VIEW = "stream_view"

    INQUIRY_LIST = "inquiry_list"
    INQUIRY_VIEW = "inquiry_view"
    INQUIRY_RESPOND = "inquiry_respond"
    INQUIRY_ALL = "inquiry_all"

    @classmethod
    def get_valid_permissions_for_resource_type(cls, resource_type):
        """
        Return valid permissions for the provided resource type.

        :rtype: ``list``
        """
        valid_permissions = RESOURCE_TYPE_TO_PERMISSION_TYPES_MAP[resource_type]
        return valid_permissions

    @classmethod
    def get_resource_type(cls, permission_type):
        """
        Retrieve resource type from the provided permission type.

        :rtype: ``str``
        """
        # Special case for:
        # * PACK_VIEWS_INDEX_HEALTH
        # * EXECUTION_VIEWS_FILTERS_LIST
        if permission_type == PermissionType.PACK_VIEWS_INDEX_HEALTH:
            return ResourceType.PACK
        elif permission_type == PermissionType.EXECUTION_VIEWS_FILTERS_LIST:
            return ResourceType.EXECUTION

        split = permission_type.split("_")
        if len(split) < 2:
            raise ValueError(
                f"The permission_type {permission_type} doesn't have an underscore."
            )

        return "_".join(split[:-1])

    @classmethod
    def get_permission_name(cls, permission_type):
        """
        Retrieve permission name from the provided permission type.

        :rtype: ``str``
        """
        split = permission_type.split("_")
        if len(split) < 2:
            raise ValueError(
                f"The permission_type {permission_type} doesn't have an underscore."
            )

        # Special case for PACK_VIEWS_INDEX_HEALTH
        if permission_type == PermissionType.PACK_VIEWS_INDEX_HEALTH:
            split = permission_type.split("_", 1)
            return split[1]

        return split[-1]

    @classmethod
    def get_permission_description(cls, permission_type):
        """
        Retrieve a description for the provided permission_type.

        :rtype: ``str``
        """
        description = PERMISION_TYPE_TO_DESCRIPTION_MAP[permission_type]
        return description

    @classmethod
    def get_permission_type(cls, resource_type, permission_name):
        """
        Retrieve permission type enum value for the provided resource type and permission name.

        :rtype: ``str``
        """
        # Special case for sensor type (sensor_type -> sensor)
        if resource_type == ResourceType.SENSOR:
            resource_type = "sensor"

        permission_enum = "%s_%s" % (resource_type.upper(), permission_name.upper())
        result = getattr(cls, permission_enum, None)

        if not result:
            raise ValueError(
                'Unsupported permission type for type "%s" and name "%s"'
                % (resource_type, permission_name)
            )

        return result


class ResourceType(Enum):
    """
    Resource types on which permissions can be granted.
    """

    RUNNER = SystemResourceType.RUNNER_TYPE

    PACK = SystemResourceType.PACK
    SENSOR = SystemResourceType.SENSOR_TYPE
    ACTION = SystemResourceType.ACTION
    ACTION_ALIAS = SystemResourceType.ACTION_ALIAS
    RULE = SystemResourceType.RULE
    RULE_ENFORCEMENT = SystemResourceType.RULE_ENFORCEMENT
    POLICY_TYPE = SystemResourceType.POLICY_TYPE
    POLICY = SystemResourceType.POLICY

    EXECUTION = SystemResourceType.EXECUTION
    KEY_VALUE_PAIR = SystemResourceType.KEY_VALUE_PAIR
    WEBHOOK = SystemResourceType.WEBHOOK
    TIMER = SystemResourceType.TIMER
    API_KEY = SystemResourceType.API_KEY
    TRACE = SystemResourceType.TRACE
    TRIGGER = SystemResourceType.TRIGGER
    STREAM = SystemResourceType.STREAM
    INQUIRY = SystemResourceType.INQUIRY


class SystemRole(Enum):
    """
    Default system roles which can't be manipulated (modified or removed).
    """

    SYSTEM_ADMIN = "system_admin"  # Special role which can't be revoked.
    ADMIN = "admin"
    OBSERVER = "observer"


# Maps a list of available permission types for each resource
RESOURCE_TYPE_TO_PERMISSION_TYPES_MAP = {
    ResourceType.RUNNER: [
        PermissionType.RUNNER_LIST,
        PermissionType.RUNNER_VIEW,
        PermissionType.RUNNER_MODIFY,
        PermissionType.RUNNER_ALL,
    ],
    ResourceType.PACK: [
        PermissionType.PACK_LIST,
        PermissionType.PACK_VIEW,
        PermissionType.PACK_CREATE,
        PermissionType.PACK_MODIFY,
        PermissionType.PACK_DELETE,
        PermissionType.PACK_INSTALL,
        PermissionType.PACK_UNINSTALL,
        PermissionType.PACK_REGISTER,
        PermissionType.PACK_CONFIG,
        PermissionType.PACK_SEARCH,
        PermissionType.PACK_VIEWS_INDEX_HEALTH,
        PermissionType.PACK_ALL,
        PermissionType.SENSOR_VIEW,
        PermissionType.SENSOR_MODIFY,
        PermissionType.SENSOR_ALL,
        PermissionType.ACTION_VIEW,
        PermissionType.ACTION_CREATE,
        PermissionType.ACTION_MODIFY,
        PermissionType.ACTION_DELETE,
        PermissionType.ACTION_EXECUTE,
        PermissionType.ACTION_ALL,
        PermissionType.ACTION_ALIAS_VIEW,
        PermissionType.ACTION_ALIAS_CREATE,
        PermissionType.ACTION_ALIAS_MODIFY,
        PermissionType.ACTION_ALIAS_DELETE,
        PermissionType.ACTION_ALIAS_ALL,
        PermissionType.RULE_VIEW,
        PermissionType.RULE_CREATE,
        PermissionType.RULE_MODIFY,
        PermissionType.RULE_DELETE,
        PermissionType.RULE_ALL,
    ],
    ResourceType.SENSOR: [
        PermissionType.SENSOR_LIST,
        PermissionType.SENSOR_VIEW,
        PermissionType.SENSOR_MODIFY,
        PermissionType.SENSOR_ALL,
    ],
    ResourceType.ACTION: [
        PermissionType.ACTION_LIST,
        PermissionType.ACTION_VIEW,
        PermissionType.ACTION_CREATE,
        PermissionType.ACTION_MODIFY,
        PermissionType.ACTION_DELETE,
        PermissionType.ACTION_EXECUTE,
        PermissionType.ACTION_ALL,
    ],
    ResourceType.ACTION_ALIAS: [
        PermissionType.ACTION_ALIAS_LIST,
        PermissionType.ACTION_ALIAS_VIEW,
        PermissionType.ACTION_ALIAS_CREATE,
        PermissionType.ACTION_ALIAS_MODIFY,
        PermissionType.ACTION_ALIAS_MATCH,
        PermissionType.ACTION_ALIAS_HELP,
        PermissionType.ACTION_ALIAS_DELETE,
        PermissionType.ACTION_ALIAS_ALL,
    ],
    ResourceType.RULE: [
        PermissionType.RULE_LIST,
        PermissionType.RULE_VIEW,
        PermissionType.RULE_CREATE,
        PermissionType.RULE_MODIFY,
        PermissionType.RULE_DELETE,
        PermissionType.RULE_ALL,
    ],
    ResourceType.RULE_ENFORCEMENT: [
        PermissionType.RULE_ENFORCEMENT_LIST,
        PermissionType.RULE_ENFORCEMENT_VIEW,
    ],
    ResourceType.EXECUTION: [
        PermissionType.EXECUTION_LIST,
        PermissionType.EXECUTION_VIEW,
        PermissionType.EXECUTION_RE_RUN,
        PermissionType.EXECUTION_STOP,
        PermissionType.EXECUTION_ALL,
        PermissionType.EXECUTION_VIEWS_FILTERS_LIST,
    ],
    ResourceType.KEY_VALUE_PAIR: [
        PermissionType.KEY_VALUE_PAIR_LIST,
        PermissionType.KEY_VALUE_PAIR_VIEW,
        PermissionType.KEY_VALUE_PAIR_SET,
        PermissionType.KEY_VALUE_PAIR_DELETE,
        PermissionType.KEY_VALUE_PAIR_ALL,
    ],
    ResourceType.WEBHOOK: [
        PermissionType.WEBHOOK_LIST,
        PermissionType.WEBHOOK_VIEW,
        PermissionType.WEBHOOK_CREATE,
        PermissionType.WEBHOOK_SEND,
        PermissionType.WEBHOOK_DELETE,
        PermissionType.WEBHOOK_ALL,
    ],
    ResourceType.TIMER: [
        PermissionType.TIMER_LIST,
        PermissionType.TIMER_VIEW,
        PermissionType.TIMER_ALL,
    ],
    ResourceType.API_KEY: [
        PermissionType.API_KEY_LIST,
        PermissionType.API_KEY_VIEW,
        PermissionType.API_KEY_CREATE,
        PermissionType.API_KEY_MODIFY,
        PermissionType.API_KEY_DELETE,
        PermissionType.API_KEY_ALL,
    ],
    ResourceType.TRACE: [
        PermissionType.TRACE_LIST,
        PermissionType.TRACE_VIEW,
        PermissionType.TRACE_ALL,
    ],
    ResourceType.TRIGGER: [
        PermissionType.TRIGGER_LIST,
        PermissionType.TRIGGER_VIEW,
        PermissionType.TRIGGER_ALL,
    ],
    ResourceType.POLICY_TYPE: [
        PermissionType.POLICY_TYPE_LIST,
        PermissionType.POLICY_TYPE_VIEW,
        PermissionType.POLICY_TYPE_ALL,
    ],
    ResourceType.POLICY: [
        PermissionType.POLICY_LIST,
        PermissionType.POLICY_VIEW,
        PermissionType.POLICY_CREATE,
        PermissionType.POLICY_MODIFY,
        PermissionType.POLICY_DELETE,
        PermissionType.POLICY_ALL,
    ],
    ResourceType.INQUIRY: [
        PermissionType.INQUIRY_LIST,
        PermissionType.INQUIRY_VIEW,
        PermissionType.INQUIRY_RESPOND,
        PermissionType.INQUIRY_ALL,
    ],
}

ALL_PERMISSION_TYPES = list(RESOURCE_TYPE_TO_PERMISSION_TYPES_MAP.values())
ALL_PERMISSION_TYPES = list(itertools.chain(*ALL_PERMISSION_TYPES))
LIST_PERMISSION_TYPES = [
    permission_type
    for permission_type in ALL_PERMISSION_TYPES
    if permission_type.endswith("_list")
]

# List of global permissions (ones which don't apply to a specific resource)
GLOBAL_PERMISSION_TYPES = [
    # Pack global permission types
    PermissionType.PACK_INSTALL,
    PermissionType.PACK_UNINSTALL,
    PermissionType.PACK_CREATE,
    PermissionType.PACK_REGISTER,
    PermissionType.PACK_CONFIG,
    PermissionType.PACK_SEARCH,
    PermissionType.PACK_VIEWS_INDEX_HEALTH,
    # Action alias global permission types
    PermissionType.ACTION_ALIAS_MATCH,
    PermissionType.ACTION_ALIAS_HELP,
    # API key global permission types
    PermissionType.API_KEY_CREATE,
    # Policy global permission types
    PermissionType.POLICY_CREATE,
    # Execution
    PermissionType.EXECUTION_VIEWS_FILTERS_LIST,
    # Stream
    PermissionType.STREAM_VIEW,
    # Inquiry
    PermissionType.INQUIRY_LIST,
    PermissionType.INQUIRY_RESPOND,
    PermissionType.INQUIRY_VIEW,
] + LIST_PERMISSION_TYPES

GLOBAL_PACK_PERMISSION_TYPES = [
    permission_type
    for permission_type in GLOBAL_PERMISSION_TYPES
    if permission_type.startswith("pack_")
]


# Maps a permission type to the corresponding description
PERMISION_TYPE_TO_DESCRIPTION_MAP = {
    PermissionType.PACK_LIST: "Ability to list (view all) packs.",
    PermissionType.PACK_VIEW: "Ability to view a pack.",
    PermissionType.PACK_CREATE: "Ability to create a new pack.",
    PermissionType.PACK_MODIFY: "Ability to modify (update) an existing pack.",
    PermissionType.PACK_DELETE: "Ability to delete an existing pack.",
    PermissionType.PACK_INSTALL: "Ability to install packs.",
    PermissionType.PACK_UNINSTALL: "Ability to uninstall packs.",
    PermissionType.PACK_REGISTER: "Ability to register packs and corresponding resources.",
    PermissionType.PACK_CONFIG: "Ability to configure a pack.",
    PermissionType.PACK_SEARCH: "Ability to query registry and search packs.",
    PermissionType.PACK_VIEWS_INDEX_HEALTH: "Ability to query health of pack registries.",
    PermissionType.PACK_ALL: (
        "Ability to perform all the supported operations on a particular " "pack."
    ),
    PermissionType.SENSOR_LIST: "Ability to list (view all) sensors.",
    PermissionType.SENSOR_VIEW: "Ability to view a sensor",
    PermissionType.SENSOR_MODIFY: (
        "Ability to modify (update) an existing sensor. Also implies "
        '"sensor_type_view" permission.'
    ),
    PermissionType.SENSOR_ALL: (
        "Ability to perform all the supported operations on a particular " "sensor."
    ),
    PermissionType.ACTION_LIST: "Ability to list (view all) actions.",
    PermissionType.ACTION_VIEW: "Ability to view an action.",
    PermissionType.ACTION_CREATE: (
        'Ability to create a new action. Also implies "action_view" ' "permission."
    ),
    PermissionType.ACTION_MODIFY: (
        "Ability to modify (update) an existing action. Also implies "
        '"action_view" permission.'
    ),
    PermissionType.ACTION_DELETE: (
        "Ability to delete an existing action. Also implies "
        '"action_view" permission.'
    ),
    PermissionType.ACTION_EXECUTE: (
        "Ability to execute (run) an action. Also implies " '"action_view" permission.'
    ),
    PermissionType.ACTION_ALL: (
        "Ability to perform all the supported operations on a particular " "action."
    ),
    PermissionType.ACTION_ALIAS_LIST: "Ability to list (view all) action aliases.",
    PermissionType.ACTION_ALIAS_VIEW: "Ability to view an action alias.",
    PermissionType.ACTION_ALIAS_CREATE: (
        "Ability to create a new action alias. Also implies"
        ' "action_alias_view" permission.'
    ),
    PermissionType.ACTION_ALIAS_MODIFY: (
        "Ability to modify (update) an existing action alias. "
        'Also implies "action_alias_view" permission.'
    ),
    PermissionType.ACTION_ALIAS_MATCH: (
        "Ability to use action alias match API endpoint."
    ),
    PermissionType.ACTION_ALIAS_HELP: (
        "Ability to use action alias help API endpoint."
    ),
    PermissionType.ACTION_ALIAS_DELETE: (
        "Ability to delete an existing action alias. Also "
        'implies "action_alias_view" permission.'
    ),
    PermissionType.ACTION_ALIAS_ALL: (
        "Ability to perform all the supported operations on a "
        "particular action alias."
    ),
    PermissionType.EXECUTION_LIST: "Ability to list (view all) executions.",
    PermissionType.EXECUTION_VIEW: "Ability to view an execution.",
    PermissionType.EXECUTION_RE_RUN: "Ability to create a new action.",
    PermissionType.EXECUTION_STOP: "Ability to stop (cancel) a running execution.",
    PermissionType.EXECUTION_ALL: (
        "Ability to perform all the supported operations on a " "particular execution."
    ),
    PermissionType.EXECUTION_VIEWS_FILTERS_LIST: (
        "Ability view all the distinct execution " "filters."
    ),
    PermissionType.RULE_LIST: "Ability to list (view all) rules.",
    PermissionType.RULE_VIEW: "Ability to view a rule.",
    PermissionType.RULE_CREATE: (
        'Ability to create a new rule. Also implies "rule_view" ' "permission"
    ),
    PermissionType.RULE_MODIFY: (
        "Ability to modify (update) an existing rule. Also implies "
        '"rule_view" permission.'
    ),
    PermissionType.RULE_DELETE: (
        'Ability to delete an existing rule. Also implies "rule_view" ' "permission."
    ),
    PermissionType.RULE_ALL: (
        "Ability to perform all the supported operations on a particular " "rule."
    ),
    PermissionType.RULE_ENFORCEMENT_LIST: "Ability to list (view all) rule enforcements.",
    PermissionType.RULE_ENFORCEMENT_VIEW: "Ability to view a rule enforcement.",
    PermissionType.RUNNER_LIST: "Ability to list (view all) runners.",
    PermissionType.RUNNER_VIEW: "Ability to view a runner.",
    PermissionType.RUNNER_MODIFY: (
        "Ability to modify (update) an existing runner. Also implies "
        '"runner_type_view" permission.'
    ),
    PermissionType.RUNNER_ALL: (
        "Ability to perform all the supported operations on a particular " "runner."
    ),
    PermissionType.WEBHOOK_LIST: "Ability to list (view all) webhooks.",
    PermissionType.WEBHOOK_VIEW: ("Ability to view a webhook."),
    PermissionType.WEBHOOK_CREATE: ("Ability to create a new webhook."),
    PermissionType.WEBHOOK_SEND: (
        "Ability to send / POST data to an existing webhook."
    ),
    PermissionType.WEBHOOK_DELETE: ("Ability to delete an existing webhook."),
    PermissionType.WEBHOOK_ALL: (
        "Ability to perform all the supported operations on a particular " "webhook."
    ),
    PermissionType.TIMER_LIST: "Ability to list (view all) timers.",
    PermissionType.TIMER_VIEW: ("Ability to view a timer."),
    PermissionType.TIMER_ALL: (
        "Ability to perform all the supported operations on timers"
    ),
    PermissionType.API_KEY_LIST: "Ability to list (view all) API keys.",
    PermissionType.API_KEY_VIEW: ("Ability to view an API Key."),
    PermissionType.API_KEY_CREATE: ("Ability to create a new API Key."),
    PermissionType.API_KEY_MODIFY: (
        "Ability to modify (update) an existing API key. Also implies "
        '"api_key_view" permission.'
    ),
    PermissionType.API_KEY_DELETE: ("Ability to delete an existing API Keys."),
    PermissionType.API_KEY_ALL: (
        "Ability to perform all the supported operations on an API Key."
    ),
    PermissionType.KEY_VALUE_PAIR_LIST: ("Ability to list (view all) Key-Value Pairs."),
    PermissionType.KEY_VALUE_PAIR_VIEW: ("Ability to view Key-Value Pairs."),
    PermissionType.KEY_VALUE_PAIR_SET: ("Ability to set a Key-Value Pair."),
    PermissionType.KEY_VALUE_PAIR_DELETE: (
        "Ability to delete an existing Key-Value Pair."
    ),
    PermissionType.KEY_VALUE_PAIR_ALL: (
        "Ability to perform all the supported operations on a Key-Value Pair."
    ),
    PermissionType.TRACE_LIST: ("Ability to list (view all) traces."),
    PermissionType.TRACE_VIEW: ("Ability to view a trace."),
    PermissionType.TRACE_ALL: (
        "Ability to perform all the supported operations on traces."
    ),
    PermissionType.TRIGGER_LIST: ("Ability to list (view all) triggers."),
    PermissionType.TRIGGER_VIEW: ("Ability to view a trigger."),
    PermissionType.TRIGGER_ALL: (
        "Ability to perform all the supported operations on triggers."
    ),
    PermissionType.POLICY_TYPE_LIST: ("Ability to list (view all) policy types."),
    PermissionType.POLICY_TYPE_VIEW: ("Ability to view a policy types."),
    PermissionType.POLICY_TYPE_ALL: (
        "Ability to perform all the supported operations on policy" " types."
    ),
    PermissionType.POLICY_LIST: "Ability to list (view all) policies.",
    PermissionType.POLICY_VIEW: ("Ability to view a policy."),
    PermissionType.POLICY_CREATE: ("Ability to create a new policy."),
    PermissionType.POLICY_MODIFY: ("Ability to modify an existing policy."),
    PermissionType.POLICY_DELETE: ("Ability to delete an existing policy."),
    PermissionType.POLICY_ALL: (
        "Ability to perform all the supported operations on a particular " "policy."
    ),
    PermissionType.STREAM_VIEW: (
        "Ability to view / listen to the events on the stream API " "endpoint."
    ),
    PermissionType.INQUIRY_LIST: "Ability to list existing Inquiries",
    PermissionType.INQUIRY_VIEW: "Ability to view an existing Inquiry. Also implies "
    '"inquiry_respond" permission.',
    PermissionType.INQUIRY_RESPOND: "Ability to respond to an existing Inquiry (in general - user "
    "still needs access per specific inquiry parameters). Also "
    'implies "inquiry_view" permission.',
    PermissionType.INQUIRY_ALL: (
        "Ability to perform all supported operations on a particular " "Inquiry."
    ),
}


def get_resource_permission_types_with_descriptions():
    """
    Return available permission types for each resource types with corresponding descriptions.

    :rtype: ``dict`
    """
    result = {}

    for resource_type, permission_types in six.iteritems(
        RESOURCE_TYPE_TO_PERMISSION_TYPES_MAP
    ):
        result[resource_type] = {}
        for permission_type in permission_types:
            result[resource_type][permission_type] = PERMISION_TYPE_TO_DESCRIPTION_MAP[
                permission_type
            ]

    return result
