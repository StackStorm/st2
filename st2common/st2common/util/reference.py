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
from st2common.exceptions import db
from st2common.models.system.common import ResourceReference


def get_ref_from_model(model):
    if model is None:
        raise ValueError("Model has None value.")
    model_id = getattr(model, "id", None)
    if model_id is None:
        raise db.StackStormDBObjectMalformedError(
            "model %s must contain id." % str(model)
        )
    reference = {"id": str(model_id), "name": getattr(model, "name", None)}
    return reference


def get_model_from_ref(db_api, reference):
    if reference is None:
        raise db.StackStormDBObjectNotFoundError("No reference supplied.")
    model_id = reference.get("id", None)
    if model_id is not None:
        return db_api.get_by_id(model_id)
    model_name = reference.get("name", None)
    if model_name is None:
        raise db.StackStormDBObjectNotFoundError("Both name and id are None.")
    return db_api.get_by_name(model_name)


def get_model_by_resource_ref(db_api, ref):
    """
    Retrieve a DB model based on the resource reference.

    :param db_api: Class of the object to retrieve.
    :type db_api: ``object``

    :param ref: Resource reference.
    :type ref: ``str``

    :return: Retrieved object.
    """
    ref_obj = ResourceReference.from_string_reference(ref=ref)
    result = db_api.query(name=ref_obj.name, pack=ref_obj.pack).first()
    return result


def get_resource_ref_from_model(model):
    """
    Return a ResourceReference given db_model.

    :param model: DB model that contains name and pack.
    :type model: ``object``

    :return: ResourceReference.
    """
    try:
        name = model.name
        pack = model.pack
    except AttributeError:
        raise Exception(
            "Cannot build ResourceReference for model: %s. Name or pack missing."
            % model
        )
    return ResourceReference(name=name, pack=pack)


def get_str_resource_ref_from_model(model):
    """
    Return a resource reference as string given db_model.

    :param model: DB model that contains name and pack.
    :type model: ``object``

    :return: String representation of ResourceReference.
    """
    return get_resource_ref_from_model(model).ref
