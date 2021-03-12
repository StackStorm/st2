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

from st2common import log as logging
from st2common.constants.triggers import CRON_TIMER_TRIGGER_REF
from st2common.exceptions.sensors import TriggerTypeRegistrationException
from st2common.exceptions.triggers import TriggerDoesNotExistException
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.exceptions.db import StackStormDBObjectConflictError
from st2common.models.api.trigger import TriggerAPI, TriggerTypeAPI
from st2common.models.system.common import ResourceReference
from st2common.persistence.trigger import Trigger, TriggerType

__all__ = [
    "add_trigger_models",
    "get_trigger_db_by_ref",
    "get_trigger_db_by_id",
    "get_trigger_db_by_uid",
    "get_trigger_db_by_ref_or_dict",
    "get_trigger_db_given_type_and_params",
    "get_trigger_type_db",
    "create_trigger_db",
    "create_trigger_type_db",
    "create_or_update_trigger_db",
    "create_or_update_trigger_type_db",
]

LOG = logging.getLogger(__name__)


def get_trigger_db_given_type_and_params(type=None, parameters=None):
    try:
        parameters = parameters or {}
        trigger_dbs = Trigger.query(type=type, parameters=parameters)

        trigger_db = trigger_dbs[0] if len(trigger_dbs) > 0 else None

        # NOTE: This is a work-around which we might be able to remove once we upgrade
        # pymongo and mongoengine
        # Work around for cron-timer when in some scenarios finding an object fails when Python
        # value types are unicode :/
        is_cron_trigger = type == CRON_TIMER_TRIGGER_REF
        has_parameters = bool(parameters)

        if not trigger_db and six.PY2 and is_cron_trigger and has_parameters:
            non_unicode_literal_parameters = {}
            for key, value in six.iteritems(parameters):
                key = key.encode("utf-8")

                if isinstance(value, six.text_type):
                    # We only encode unicode to str
                    value = value.encode("utf-8")

                non_unicode_literal_parameters[key] = value
            parameters = non_unicode_literal_parameters

            trigger_dbs = Trigger.query(
                type=type, parameters=non_unicode_literal_parameters
            ).no_cache()

            # Note: We need to directly access the object, using len or accessing the query set
            # twice won't work - there seems to bug a bug with cursor where accessing it twice
            # will throw an exception
            try:
                trigger_db = trigger_dbs[0]
            except IndexError:
                trigger_db = None

        if not parameters and not trigger_db:
            # We need to do double query because some TriggeDB objects without
            # parameters have "parameters" attribute stored in the db and others
            # don't
            trigger_db = Trigger.query(type=type, parameters=None).first()

        return trigger_db
    except StackStormDBObjectNotFoundError as e:
        LOG.debug(
            'Database lookup for type="%s" parameters="%s" resulted '
            + "in exception : %s.",
            type,
            parameters,
            e,
            exc_info=True,
        )
        return None


def get_trigger_db_by_ref_or_dict(trigger):
    """
    Retrieve TriggerDB object based on the trigger reference of based on a
    provided dictionary with trigger attributes.
    """
    # TODO: This is nasty, this should take a unique reference and not a dict
    if isinstance(trigger, six.string_types):
        trigger_db = get_trigger_db_by_ref(trigger)
    else:
        # If id / uid is available we try to look up Trigger by id. This way we can avoid bug in
        # pymongo / mongoengine related to "parameters" dictionary lookups
        trigger_id = trigger.get("id", None)
        trigger_uid = trigger.get("uid", None)

        # TODO: Remove parameters dictionary look up when we can confirm each trigger dictionary
        # passed to this method always contains id or uid
        if trigger_id:
            LOG.debug("Looking up TriggerDB by id: %s", trigger_id)
            trigger_db = get_trigger_db_by_id(id=trigger_id)
        elif trigger_uid:
            LOG.debug("Looking up TriggerDB by uid: %s", trigger_uid)
            trigger_db = get_trigger_db_by_uid(uid=trigger_uid)
        else:
            # Last resort - look it up by parameters
            trigger_type = trigger.get("type", None)
            parameters = trigger.get("parameters", {})

            LOG.debug(
                "Looking up TriggerDB by type and parameters: type=%s, parameters=%s",
                trigger_type,
                parameters,
            )
            trigger_db = get_trigger_db_given_type_and_params(
                type=trigger_type, parameters=parameters
            )

    return trigger_db


def get_trigger_db_by_id(id):
    """
    Returns the trigger object from db given a trigger id.

    :param ref: Reference to the trigger db object.
    :type ref: ``str``

    :rtype: ``object``
    """
    try:
        return Trigger.get_by_id(id)
    except StackStormDBObjectNotFoundError as e:
        LOG.debug(
            'Database lookup for id="%s" resulted in exception : %s.',
            id,
            e,
            exc_info=True,
        )

    return None


def get_trigger_db_by_uid(uid):
    """
    Returns the trigger object from db given a trigger uid.

    :param ref: Reference to the trigger db object.
    :type ref: ``str``

    :rtype: ``object``
    """
    try:
        return Trigger.get_by_uid(uid)
    except StackStormDBObjectNotFoundError as e:
        LOG.debug(
            'Database lookup for uid="%s" resulted in exception : %s.',
            uid,
            e,
            exc_info=True,
        )

    return None


def get_trigger_db_by_ref(ref):
    """
    Returns the trigger object from db given a string ref.

    :param ref: Reference to the trigger db object.
    :type ref: ``str``

    :rtype trigger_type: ``object``
    """
    try:
        return Trigger.get_by_ref(ref)
    except StackStormDBObjectNotFoundError as e:
        LOG.debug(
            'Database lookup for ref="%s" resulted ' + "in exception : %s.",
            ref,
            e,
            exc_info=True,
        )

    return None


def _get_trigger_db(trigger):
    # TODO: This method should die in a fire
    # XXX: Do not make this method public.

    if isinstance(trigger, dict):
        name = trigger.get("name", None)
        pack = trigger.get("pack", None)

        if name and pack:
            ref = ResourceReference.to_string_reference(name=name, pack=pack)
            return get_trigger_db_by_ref(ref)
        return get_trigger_db_given_type_and_params(
            type=trigger["type"], parameters=trigger.get("parameters", {})
        )
    else:
        raise Exception("Unrecognized object")


def get_trigger_type_db(ref):
    """
    Returns the trigger type object from db given a string ref.

    :param ref: Reference to the trigger type db object.
    :type ref: ``str``

    :rtype trigger_type: ``object``
    """
    try:
        return TriggerType.get_by_ref(ref)
    except StackStormDBObjectNotFoundError as e:
        LOG.debug(
            'Database lookup for ref="%s" resulted ' + "in exception : %s.",
            ref,
            e,
            exc_info=True,
        )

    return None


def _get_trigger_dict_given_rule(rule):
    trigger = rule.trigger
    trigger_dict = {}
    triggertype_ref = ResourceReference.from_string_reference(trigger.get("type"))
    trigger_dict["pack"] = trigger_dict.get("pack", triggertype_ref.pack)
    trigger_dict["type"] = triggertype_ref.ref
    trigger_dict["parameters"] = rule.trigger.get("parameters", {})

    return trigger_dict


def create_trigger_db(trigger_api):
    # TODO: This is used only in trigger API controller. We should get rid of this.
    trigger_ref = ResourceReference.to_string_reference(
        name=trigger_api.name, pack=trigger_api.pack
    )
    trigger_db = get_trigger_db_by_ref(trigger_ref)
    if not trigger_db:
        trigger_db = TriggerAPI.to_model(trigger_api)
        LOG.debug("Verified trigger and formulated TriggerDB=%s", trigger_db)
        trigger_db = Trigger.add_or_update(trigger_db)
    return trigger_db


def create_or_update_trigger_db(trigger, log_not_unique_error_as_debug=False):
    """
    Create a new TriggerDB model if one doesn't exist yet or update existing
    one.

    :param trigger: Trigger info.
    :type trigger: ``dict``
    """
    if not isinstance(trigger, dict):
        raise ValueError(
            "The trigger has a value that is not a dictionary"
            f" (was {type(trigger)})."
        )

    existing_trigger_db = _get_trigger_db(trigger)

    if existing_trigger_db:
        is_update = True
    else:
        is_update = False

    trigger_api = TriggerAPI(**trigger)
    trigger_api.validate()
    trigger_db = TriggerAPI.to_model(trigger_api)

    if is_update:
        trigger_db.id = existing_trigger_db.id

    trigger_db = Trigger.add_or_update(
        trigger_db, log_not_unique_error_as_debug=log_not_unique_error_as_debug
    )

    extra = {"trigger_db": trigger_db}

    if is_update:
        LOG.audit("Trigger updated. Trigger.id=%s" % (trigger_db.id), extra=extra)
    else:
        LOG.audit("Trigger created. Trigger.id=%s" % (trigger_db.id), extra=extra)

    return trigger_db


def create_trigger_db_from_rule(rule):
    trigger_dict = _get_trigger_dict_given_rule(rule)
    existing_trigger_db = _get_trigger_db(trigger_dict)
    # For simple triggertypes (triggertype with no parameters), we create a trigger when
    # registering triggertype. So if we hit the case that there is no trigger in db but
    # parameters is empty, then this case is a run time error.
    if not trigger_dict.get("parameters", {}) and not existing_trigger_db:
        raise TriggerDoesNotExistException(
            "A simple trigger should have been created when registering "
            "triggertype. Cannot create trigger: %s." % (trigger_dict)
        )

    if not existing_trigger_db:
        trigger_db = create_or_update_trigger_db(trigger_dict)
    else:
        trigger_db = existing_trigger_db

    # Special reference counting for trigger with parameters.
    # if trigger_dict.get('parameters', None):
    #     Trigger.update(trigger_db, inc__ref_count=1)

    return trigger_db


def increment_trigger_ref_count(rule_api):
    """
    Given the rule figures out the TriggerType with parameter and increments
    reference count on the appropriate Trigger.

    :param rule_api: Rule object used to infer the Trigger.
    :type rule_api: ``RuleApi``
    """
    trigger_dict = _get_trigger_dict_given_rule(rule_api)

    # Special reference counting for trigger with parameters.
    if trigger_dict.get("parameters", None):
        trigger_db = _get_trigger_db(trigger_dict)
        Trigger.update(trigger_db, inc__ref_count=1)


def cleanup_trigger_db_for_rule(rule_db):
    # rule.trigger is actually trigger_db ref.
    existing_trigger_db = get_trigger_db_by_ref(rule_db.trigger)
    if not existing_trigger_db or not existing_trigger_db.parameters:
        # nothing to be done here so moving on.
        LOG.debug("ref_count decrement for %s not required.", existing_trigger_db)
        return
    Trigger.update(existing_trigger_db, dec__ref_count=1)
    Trigger.delete_if_unreferenced(existing_trigger_db)


def create_trigger_type_db(trigger_type, log_not_unique_error_as_debug=False):
    """
    Creates a trigger type db object in the db given trigger_type definition as dict.

    :param trigger_type: Trigger type model.
    :type trigger_type: ``dict``

    :param log_not_unique_error_as_debug: True to lot NotUnique errors under debug instead of
                                          error log level. This is to be used in scenarios where
                                          failure is non-fatal (e.g. when services register
                                          internal trigger types which is an idempotent
                                          operation).
    :type log_not_unique_error_as_debug: ``bool``

    :rtype: ``object``
    """
    trigger_type_api = TriggerTypeAPI(**trigger_type)
    trigger_type_api.validate()
    ref = ResourceReference.to_string_reference(
        name=trigger_type_api.name, pack=trigger_type_api.pack
    )
    trigger_type_db = get_trigger_type_db(ref)

    if not trigger_type_db:
        trigger_type_db = TriggerTypeAPI.to_model(trigger_type_api)
        LOG.debug("verified trigger and formulated TriggerDB=%s", trigger_type_db)
        trigger_type_db = TriggerType.add_or_update(
            trigger_type_db, log_not_unique_error_as_debug=log_not_unique_error_as_debug
        )

    return trigger_type_db


def create_shadow_trigger(trigger_type_db, log_not_unique_error_as_debug=False):
    """
    Create a shadow trigger for TriggerType with no parameters.

    :param log_not_unique_error_as_debug: True to lot NotUnique errors under debug instead of
                                          error log level. This is to be used in scenarios where
                                          failure is non-fatal (e.g. when services register
                                          internal trigger types which is an idempotent
                                          operation).
    :type log_not_unique_error_as_debug: ``bool``

    """
    trigger_type_ref = trigger_type_db.get_reference().ref

    if trigger_type_db.parameters_schema:
        LOG.debug(
            "Skip shadow trigger for TriggerType with parameters %s.", trigger_type_ref
        )
        return None

    trigger = {
        "name": trigger_type_db.name,
        "pack": trigger_type_db.pack,
        "type": trigger_type_ref,
        "parameters": {},
    }

    return create_or_update_trigger_db(
        trigger, log_not_unique_error_as_debug=log_not_unique_error_as_debug
    )


def create_or_update_trigger_type_db(trigger_type, log_not_unique_error_as_debug=False):
    """
    Create or update a trigger type db object in the db given trigger_type definition as dict.

    :param trigger_type: Trigger type model.
    :type trigger_type: ``dict``

    :param log_not_unique_error_as_debug: True to lot NotUnique errors under debug instead of
                                          error log level. This is to be used in scenarios where
                                          failure is non-fatal (e.g. when services register
                                          internal trigger types which is an idempotent
                                          operation).
    :type log_not_unique_error_as_debug: ``bool``

    :rtype: ``object``
    """
    if not isinstance(trigger_type, dict):
        raise ValueError(
            "The trigger has a value that is not a dictionary"
            f" (was {type(trigger_type)})."
        )

    trigger_type_api = TriggerTypeAPI(**trigger_type)
    trigger_type_api.validate()
    trigger_type_api = TriggerTypeAPI.to_model(trigger_type_api)

    ref = ResourceReference.to_string_reference(
        name=trigger_type_api.name, pack=trigger_type_api.pack
    )

    existing_trigger_type_db = get_trigger_type_db(ref)
    if existing_trigger_type_db:
        is_update = True
    else:
        is_update = False

    if is_update:
        trigger_type_api.id = existing_trigger_type_db.id

    try:
        trigger_type_db = TriggerType.add_or_update(
            trigger_type_api,
            log_not_unique_error_as_debug=log_not_unique_error_as_debug,
        )
    except StackStormDBObjectConflictError:
        # Operation is idempotent and trigger could have already been created by
        # another process. Ignore object already exists because it simply means
        # there was a race and object is already in the database.
        trigger_type_db = get_trigger_type_db(ref)
        is_update = True

    extra = {"trigger_type_db": trigger_type_db}

    if is_update:
        LOG.audit(
            "TriggerType updated. TriggerType.id=%s" % (trigger_type_db.id), extra=extra
        )
    else:
        LOG.audit(
            "TriggerType created. TriggerType.id=%s" % (trigger_type_db.id), extra=extra
        )

    return trigger_type_db


def _create_trigger_type(
    pack,
    name,
    description=None,
    payload_schema=None,
    parameters_schema=None,
    tags=None,
    metadata_file=None,
):
    trigger_type = {
        "name": name,
        "pack": pack,
        "description": description,
        "payload_schema": payload_schema,
        "parameters_schema": parameters_schema,
        "tags": tags,
        "metadata_file": metadata_file,
    }

    return create_or_update_trigger_type_db(trigger_type=trigger_type)


def _validate_trigger_type(trigger_type):
    """
    XXX: We need validator objects that define the required and optional fields.
    For now, manually check them.
    """
    required_fields = ["name"]
    for field in required_fields:
        if field not in trigger_type:
            raise TriggerTypeRegistrationException(
                'Invalid trigger type. Missing field "%s"' % (field)
            )


def _create_trigger(trigger_type):
    """
    :param trigger_type: TriggerType db object.
    :type trigger_type: :class:`TriggerTypeDB`
    """
    if (
        hasattr(trigger_type, "parameters_schema")
        and not trigger_type["parameters_schema"]
    ):
        trigger_dict = {
            "name": trigger_type.name,
            "pack": trigger_type.pack,
            "type": trigger_type.get_reference().ref,
        }

        try:
            return create_or_update_trigger_db(trigger=trigger_dict)
        except:
            LOG.exception("Validation failed for Trigger=%s.", trigger_dict)
            raise TriggerTypeRegistrationException(
                "Unable to create Trigger for TriggerType=%s." % trigger_type.name
            )
    else:
        LOG.debug(
            "Won't create Trigger object as TriggerType %s expects " + "parameters.",
            trigger_type,
        )
        return None


def _add_trigger_models(trigger_type):
    pack = trigger_type["pack"]
    description = trigger_type["description"] if "description" in trigger_type else ""
    payload_schema = (
        trigger_type["payload_schema"] if "payload_schema" in trigger_type else {}
    )
    parameters_schema = (
        trigger_type["parameters_schema"] if "parameters_schema" in trigger_type else {}
    )
    tags = trigger_type.get("tags", [])
    metadata_file = trigger_type.get("metadata_file", None)

    trigger_type = _create_trigger_type(
        pack=pack,
        name=trigger_type["name"],
        description=description,
        payload_schema=payload_schema,
        parameters_schema=parameters_schema,
        tags=tags,
        metadata_file=metadata_file,
    )
    trigger = _create_trigger(trigger_type=trigger_type)
    return (trigger_type, trigger)


def add_trigger_models(trigger_types):
    """
    Register trigger types.

    :param trigger_types: A list of triggers to register.
    :type trigger_types: ``list`` of ``dict``

    :rtype: ``list`` of ``tuple`` (trigger_type, trigger)
    """
    [
        r
        for r in (
            _validate_trigger_type(trigger_type) for trigger_type in trigger_types
        )
        if r is not None
    ]

    result = []
    for trigger_type in trigger_types:
        item = _add_trigger_models(trigger_type=trigger_type)

        if item:
            result.append(item)

    return result
