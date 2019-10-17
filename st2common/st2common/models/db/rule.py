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

from mongoengine.queryset import Q
from st2common.persistence.action import Action
from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.constants.types import ResourceType
from st2common.util.secrets import get_secret_parameters
from st2common.util.secrets import mask_secret_parameters


class RuleTypeDB(stormbase.StormBaseDB):
    enabled = me.BooleanField(
        default=True,
        help_text='A flag indicating whether the runner for this type is enabled.')
    parameters = me.DictField(
        help_text='The specification for parameters for the action.',
        default={})


class RuleTypeSpecDB(me.EmbeddedDocument):
    ref = me.StringField(unique=False,
                         help_text='Type of rule.',
                         default='standard')
    parameters = me.DictField(default={})

    def __str__(self):
        result = []
        result.append('RuleTypeSpecDB@')
        result.append(str(id(self)))
        result.append('(ref="%s", ' % self.ref)
        result.append('parameters="%s")' % self.parameters)
        return ''.join(result)


class ActionExecutionSpecDB(me.EmbeddedDocument):
    ref = me.StringField(required=True, unique=False)
    parameters = me.DictField()

    def __str__(self):
        result = []
        result.append('ActionExecutionSpecDB@')
        result.append(str(id(self)))
        result.append('(ref="%s", ' % self.ref)
        result.append('parameters="%s")' % self.parameters)
        return ''.join(result)


class RuleDB(stormbase.StormFoundationDB, stormbase.TagsMixin,
             stormbase.ContentPackResourceMixin, stormbase.UIDFieldMixin):
    """Specifies the action to invoke on the occurrence of a Trigger. It
    also includes the transformation to perform to match the impedance
    between the payload of a TriggerInstance and input of a action.
    Attribute:
        trigger: Trigger that trips this rule.
        criteria:
        action: Action to execute when the rule is tripped.
        status: enabled or disabled. If disabled occurrence of the trigger
        does not lead to execution of a action and vice-versa.
    """
    RESOURCE_TYPE = ResourceType.RULE
    UID_FIELDS = ['pack', 'name']

    name = me.StringField(required=True)
    ref = me.StringField(required=True)
    description = me.StringField()
    pack = me.StringField(
        required=False,
        help_text='Name of the content pack.',
        unique_with='name')
    type = me.EmbeddedDocumentField(RuleTypeSpecDB, default=RuleTypeSpecDB())
    trigger = me.StringField()
    criteria = stormbase.EscapedDictField()
    action = me.EmbeddedDocumentField(ActionExecutionSpecDB)
    context = me.DictField(
        default={},
        help_text='Contextual info on the rule'
    )
    enabled = me.BooleanField(required=True, default=True,
                              help_text=u'Flag indicating whether the rule is enabled.')

    meta = {
        'indexes': [
            {'fields': ['enabled']},
            {'fields': ['action.ref']},
            {'fields': ['trigger']},
            {'fields': ['context.user']},
        ] + (stormbase.ContentPackResourceMixin.get_indexes() +
             stormbase.TagsMixin.get_indexes() +
             stormbase.UIDFieldMixin.get_indexes())
    }

    def mask_secrets(self, value):
        """
        Process the model dictionary and mask secret values.

        :type value: ``dict``
        :param value: Document dictionary.

        :rtype: ``dict``
        """
        result = copy.deepcopy(value)
        if('action' not in result):
            return result
        action_db = self._get_referenced_models(rule=result)

        secret_parameters = get_secret_parameters(parameters=action_db['parameters'])
        result['action']['parameters'] = mask_secret_parameters(
            parameters=result['action']['parameters'],
            secret_parameters=secret_parameters)

        return result

    def _get_referenced_models(self, rule):
        """
        Return the action model referenced from rule.

        :type rule: ``dict``
        :param rule: rule

        :rtype: ``ActionDB``
        """
        action_ref = rule['action']['ref']
        def ref_query_args(ref):
            return {'ref': ref}
        action_db = self._get_entity(model_persistence=Action,
                                     ref=action_ref,
                                     query_args=ref_query_args)

        return action_db

    def _get_entity(self, model_persistence, ref, query_args):
        q = Q(**query_args(ref))

        if q:
            return model_persistence._get_impl().model.objects(q).first()

        return None

    def __init__(self, *args, **values):
        super(RuleDB, self).__init__(*args, **values)
        self.ref = self.get_reference().ref
        self.uid = self.get_uid()


rule_access = MongoDBAccess(RuleDB)
rule_type_access = MongoDBAccess(RuleTypeDB)

MODELS = [RuleDB]
