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

import copy

import mongoengine as me

from st2common.models.db import stormbase
from st2common.fields import JSONDictEscapedFieldCompatibilityField
from st2common.fields import ComplexDateTimeField
from st2common.util import date as date_utils
from st2common.util import output_schema
from oslo_config import cfg

from st2common.util.secrets import get_secret_parameters
from st2common.util.secrets import mask_inquiry_response
from st2common.util.secrets import mask_secret_parameters
from st2common.util.secrets import encrypt_secret_parameters
from st2common.util.crypto import read_crypto_key

from st2common.constants.types import ResourceType

__all__ = ["ActionExecutionDB", "ActionExecutionOutputDB"]


class ActionExecutionDB(stormbase.StormFoundationDB):
    RESOURCE_TYPE = ResourceType.EXECUTION
    UID_FIELDS = ["id"]

    trigger = stormbase.EscapedDictField()
    trigger_type = stormbase.EscapedDictField()
    trigger_instance = stormbase.EscapedDictField()
    rule = stormbase.EscapedDictField()
    action = stormbase.EscapedDictField(required=True)
    runner = stormbase.EscapedDictField(required=True)
    # Only the diff between the liveaction type and what is replicated
    # in the ActionExecutionDB object.
    liveaction = stormbase.EscapedDictField(required=True)
    workflow_execution = me.StringField()
    task_execution = me.StringField()
    status = me.StringField(
        required=True, help_text="The current status of the liveaction."
    )
    start_timestamp = ComplexDateTimeField(
        default=date_utils.get_datetime_utc_now,
        help_text="The timestamp when the liveaction was created.",
    )
    end_timestamp = ComplexDateTimeField(
        help_text="The timestamp when the liveaction has finished."
    )
    parameters = stormbase.EscapedDynamicField(
        default={},
        help_text="The key-value pairs passed as to the action runner & action.",
    )
    result = JSONDictEscapedFieldCompatibilityField(
        default={}, help_text="Action defined result."
    )
    result_size = me.IntField(default=0, help_text="Serialized result size in bytes")
    context = me.DictField(
        default={}, help_text="Contextual information on the action execution."
    )
    parent = me.StringField()
    children = me.ListField(field=me.StringField())
    log = me.ListField(field=me.DictField())
    delay = me.IntField(min_value=0)
    # Do not use URLField for web_url. If host doesn't have FQDN set, URLField validation blows.
    web_url = me.StringField(required=False)

    meta = {
        "indexes": [
            {"fields": ["rule.ref"]},
            {"fields": ["action.ref"]},
            {"fields": ["liveaction.id"]},
            {"fields": ["start_timestamp"]},
            {"fields": ["end_timestamp"]},
            {"fields": ["status"]},
            {"fields": ["parent"]},
            {"fields": ["rule.name"]},
            {"fields": ["runner.name"]},
            {"fields": ["trigger.name"]},
            {"fields": ["trigger_type.name"]},
            {"fields": ["trigger_instance.id"]},
            {"fields": ["context.user"]},
            {"fields": ["action.ref", "status", "-start_timestamp"]},
            {"fields": ["workflow_execution"]},
            {"fields": ["task_execution"]},
        ]
    }
    encryption_key = read_crypto_key(cfg.CONF.actionrunner.encryption_key_path)

    def get_uid(self):
        # TODO Construct id from non id field:
        uid = [self.RESOURCE_TYPE, str(self.id)]  # pylint: disable=no-member
        return ":".join(uid)

    def mask_secrets(self, value):
        """
        Masks the secret parameters in input and output schema for action execution output.

        :param value: action execution object.
        :type value: ``dict``

        :return: result: action execution object with masked secret paramters in input and output schema.
        :rtype: result: ``dict``
        """

        result = copy.deepcopy(value)

        liveaction = result["liveaction"]
        parameters = {}
        # pylint: disable=no-member
        parameters.update(value.get("action", {}).get("parameters", {}))
        parameters.update(value.get("runner", {}).get("runner_parameters", {}))

        secret_parameters = get_secret_parameters(parameters=parameters)
        result["parameters"] = mask_secret_parameters(
            parameters=result.get("parameters", {}), secret_parameters=secret_parameters
        )

        if "parameters" in liveaction:
            liveaction["parameters"] = mask_secret_parameters(
                parameters=liveaction["parameters"], secret_parameters=secret_parameters
            )

            if liveaction.get("action", "") == "st2.inquiry.respond":
                # Special case to mask parameters for `st2.inquiry.respond` action
                # In this case, this execution is just a plain python action, not
                # an inquiry, so we don't natively have a handle on the response
                # schema.
                #
                # To prevent leakage, we can just mask all response fields.
                #
                # Note: The 'string' type in secret_parameters doesn't matter,
                #       it's just a placeholder to tell mask_secret_parameters()
                #       that this parameter is indeed a secret parameter and to
                #       mask it.
                result["parameters"]["response"] = mask_secret_parameters(
                    parameters=liveaction["parameters"]["response"],
                    secret_parameters={
                        p: "string" for p in liveaction["parameters"]["response"]
                    },
                )

        output_value = ActionExecutionDB.result.parse_field_value(result["result"])
        masked_output_value = output_schema.mask_secret_output(result, output_value)
        result["result"] = masked_output_value

        # TODO(mierdin): This logic should be moved to the dedicated Inquiry
        # data model once it exists.
        if self.runner.get("name") == "inquirer":
            schema = result["result"].get("schema", {})
            response = result["result"].get("response", {})

            # We can only mask response secrets if response and schema exist and are
            # not empty
            if response and schema:
                result["result"]["response"] = mask_inquiry_response(response, schema)
        return result

    def get_masked_parameters(self):
        """
        Retrieve parameters with the secrets masked.

        :rtype: ``dict``
        """
        serializable_dict = self.to_serializable_dict(mask_secrets=True)
        return serializable_dict["parameters"]

    def save(self, *args, **kwargs):
        original_parameters = copy.deepcopy(self.parameters)
        parameters = {}
        parameters.update(dict(self.action).get("parameters", {}))
        parameters.update(dict(self.runner).get("runner_parameters", {}))
        secret_parameters = get_secret_parameters(parameters=parameters)
        encrpyted_parameters = encrypt_secret_parameters(
            self.parameters, secret_parameters, self.encryption_key
        )
        self.parameters = encrpyted_parameters
        liveaction_dict = dict(self.liveaction)
        if "parameters" in liveaction_dict:
            # We need to also encrypt the parameters inside liveaction
            original_liveaction_parameters = liveaction_dict.get("parameters", {})
            encrpyted_parameters = encrypt_secret_parameters(
                original_liveaction_parameters, secret_parameters, self.encryption_key
            )
            liveaction_dict["parameters"] = encrpyted_parameters
            self.liveaction = liveaction_dict
            # We also mask response found inside parameters under liveaction.
            # As mentioned above in mask_secrets function but I don't know what should be
            # the expected behaviour as there we are making all the values because
            # the schema is unknown
        original_output_value = None
        if self.result:
            original_output_value = self.result
            schema = dict(self.action).get("output_schema")
            if schema is not None:
                self.result = output_schema.encrypt_secret_output(
                    self.encryption_key, self.result, schema
                )
                # # Need output key
                # schema = self.action.get("output_schema")
                # for key, spec in schema.items():
                #     if key in self.result and spec.get("secret", False):
                #         self.result[key] = str(symmetric_encrypt(self.encryption_key, self.result[key]))

        self = super(ActionExecutionDB, self).save(*args, **kwargs)
        # Resetting to the original values
        setattr(self, "parameters", original_parameters)
        if hasattr(self, "liveaction"):
            liveaction_dict = dict(self.liveaction)
            if "parameters" in liveaction_dict:
                liveaction_dict["parameters"] = original_liveaction_parameters
            self.liveaction = liveaction_dict

        if hasattr(self, "result") and original_output_value is not None:
            setattr(self, "result", original_output_value)
        return self

    def update(self, **kwargs):
        parameters = {}
        parameters.update(dict(self.action).get("parameters", {}))
        parameters.update(dict(self.runner).get("runner_parameters", {}))
        secret_parameters = get_secret_parameters(parameters=parameters)
        encrpyted_parameters = encrypt_secret_parameters(
            self.parameters, secret_parameters, self.encryption_key
        )
        self.parameters = encrpyted_parameters
        if "set__liveaction" in kwargs and "parameters" in kwargs["set__liveaction"]:
            encrpyted_parameters = encrypt_secret_parameters(
                kwargs["set__liveaction"]["parameters"],
                secret_parameters,
                self.encryption_key,
            )
            kwargs["set__liveaction"]["parameters"] = encrpyted_parameters
        if "set__result" in kwargs and "result" in kwargs["set__result"]:
            output_value = kwargs["set__result"]["result"]
            # Need output key
            schema = dict(self.action).get("output_schema")
            kwargs["set__result"]["result"] = output_schema.encrypt_secret_output(
                self.encryption_key, output_value, schema
            )

        if "parameters" in self.liveaction:
            original_liveaction_parameters = self.liveaction.get("parameters", {})
            encrpyted_parameters = encrypt_secret_parameters(
                original_liveaction_parameters, secret_parameters, self.encryption_key
            )
            self.liveaction.parameters = encrpyted_parameters

        return super(ActionExecutionDB, self).update(**kwargs)


class ActionExecutionOutputDB(stormbase.StormFoundationDB):
    """
    Stores output of a particular execution.

    New document is inserted dynamically when a new chunk / line is received which means you can
    simulate tail behavior by periodically reading from this collection.

    Attribute:
        execution_id: ID of the execution to which this output belongs.
        action_ref: Parent action reference.
        runner_ref: Parent action runner reference.
        timestamp: Timestamp when this output has been produced / received.
        output_type: Type of the output (e.g. stdout, stderr, output)
        data: Actual output data. This could either be line, chunk or similar, depending on the
              runner.
    """

    execution_id = me.StringField(required=True)
    action_ref = me.StringField(required=True)
    runner_ref = me.StringField(required=True)
    timestamp = ComplexDateTimeField(
        required=True, default=date_utils.get_datetime_utc_now
    )
    output_type = me.StringField(required=True, default="output")
    delay = me.IntField()

    data = me.StringField()

    meta = {
        "indexes": [
            {"fields": ["execution_id"]},
            {"fields": ["action_ref"]},
            {"fields": ["runner_ref"]},
            {"fields": ["timestamp"]},
            {"fields": ["output_type"]},
        ]
    }


MODELS = [ActionExecutionDB, ActionExecutionOutputDB]
