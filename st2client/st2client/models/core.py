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

from typing import Optional
from typing import Tuple

import os
import logging
from functools import wraps

import six
import orjson
from six.moves import urllib
from six.moves import http_client
import requests

from st2client.utils import httpclient


LOG = logging.getLogger(__name__)


def add_auth_token_to_kwargs_from_env(func):
    @wraps(func)
    def decorate(*args, **kwargs):
        if not kwargs.get("token") and os.environ.get("ST2_AUTH_TOKEN", None):
            kwargs["token"] = os.environ.get("ST2_AUTH_TOKEN")
        if not kwargs.get("api_key") and os.environ.get("ST2_API_KEY", None):
            kwargs["api_key"] = os.environ.get("ST2_API_KEY")

        return func(*args, **kwargs)

    return decorate


def parse_api_response(response: requests.models.Response) -> dict:
    """
    Utility function which parses API json response using orjson.

    requests uses simplejson, but this version uses orjson which can be up to 50% faster and that
    is especially pronounced with larger response.
    """
    # Upstream implementation is available at
    # https://github.com/psf/requests/blob/master/requests/models.py#L876
    # NOTE: It's important that we manually decode response.content attribute before passing it to
    # orjson otherwise orjson will try to decode it and will be slower.

    # Inside tests content is not always bytes
    if isinstance(response.content, str):
        data = response.content
    else:
        data = response.content.decode("utf-8")

    data = orjson.loads(data)
    return data


class Resource(object):

    # An alias to use for the resource if different than the class name.
    _alias = None

    # Display name of the resource. This may be different than its resource
    # name specifically when the resource name is composed of multiple words.
    _display_name = None

    # URL path for the resource.
    _url_path = None

    # Plural form of the resource name. This will be used to build the
    # latter part of the REST URL.
    _plural = None

    # Plural form of the resource display name.
    _plural_display_name = None

    # A list of class attributes which will be included in __repr__ return value
    _repr_attributes = []

    def __init__(self, *args, **kwargs):
        for k, v in six.iteritems(kwargs):
            setattr(self, k, v)

    def to_dict(self, exclude_attributes=None):
        """
        Return a dictionary representation of this object.

        :param exclude_attributes: Optional list of attributes to exclude.
        :type exclude_attributes: ``list``

        :rtype: ``dict``
        """
        exclude_attributes = exclude_attributes or []

        attributes = list(self.__dict__.keys())
        attributes = [
            attr
            for attr in attributes
            if not attr.startswith("__") and attr not in exclude_attributes
        ]

        result = {}
        for attribute in attributes:
            value = getattr(self, attribute, None)
            result[attribute] = value

        return result

    @classmethod
    def get_alias(cls):
        return cls._alias if cls._alias else cls.__name__

    @classmethod
    def get_display_name(cls):
        return cls._display_name if cls._display_name else cls.__name__

    @classmethod
    def get_plural_name(cls):
        if not cls._plural:
            raise Exception(
                "The %s class is missing class attributes "
                "in its definition." % cls.__name__
            )
        return cls._plural

    @classmethod
    def get_plural_display_name(cls):
        return cls._plural_display_name if cls._plural_display_name else cls._plural

    @classmethod
    def get_url_path_name(cls):
        if cls._url_path:
            return cls._url_path

        return cls.get_plural_name().lower()

    def serialize(self):
        return dict(
            (k, v) for k, v in six.iteritems(self.__dict__) if not k.startswith("_")
        )

    @classmethod
    def deserialize(cls, doc):
        if type(doc) is not dict:
            doc = orjson.loads(doc)
        return cls(**doc)

    def __str__(self):
        return str(self.__repr__())

    def __repr__(self):
        if not self._repr_attributes:
            return super(Resource, self).__repr__()

        attributes = []
        for attribute in self._repr_attributes:
            value = getattr(self, attribute, None)
            attributes.append("%s=%s" % (attribute, value))

        attributes = ",".join(attributes)
        class_name = self.__class__.__name__
        result = "<%s %s>" % (class_name, attributes)
        return result


class ResourceManager(object):
    def __init__(
        self,
        resource: str,
        endpoint: str,
        cacert: Optional[str] = None,
        debug: bool = False,
        basic_auth: Optional[Tuple[str, str]] = None,
    ):
        """
        :param resource: Name of the resource to operate on.
        :param endpoint: API endpoint URL.
        :param cacert: Optional path to CA cert to use to validate the server side cert.
        :param debug: True to enable debug mode where additional debug information will be logged.
        :param basic_auth: Optional additional basic auth credentials in tuple(username, password)
                           notation.
        """
        self.resource = resource
        self.endpoint = endpoint
        self.cacert = cacert
        self.debug = debug
        self.basic_auth = basic_auth
        self.client = httpclient.HTTPClient(
            endpoint, cacert=cacert, debug=debug, basic_auth=basic_auth
        )

    @staticmethod
    def handle_error(response):
        try:
            content = parse_api_response(response)
            fault = content.get("faultstring", "") if content else ""
            if fault:
                response.reason += "\nMESSAGE: %s" % fault
        except Exception as e:
            response.reason += (
                "\nUnable to retrieve detailed message "
                "from the HTTP response. %s\n" % six.text_type(e)
            )
        response.raise_for_status()

    @add_auth_token_to_kwargs_from_env
    def get_all(self, **kwargs):
        # TODO: This is ugly, stop abusing kwargs
        url = "/%s" % self.resource.get_url_path_name()
        limit = kwargs.pop("limit", None)
        pack = kwargs.pop("pack", None)
        prefix = kwargs.pop("prefix", None)
        user = kwargs.pop("user", None)
        offset = kwargs.pop("offset", 0)

        params = kwargs.pop("params", {})

        if limit:
            params["limit"] = limit

        if pack:
            params["pack"] = pack

        if prefix:
            params["prefix"] = prefix

        if user:
            params["user"] = user

        if offset:
            params["offset"] = offset

        response = self.client.get(url=url, params=params, **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)
        return [
            self.resource.deserialize(item) for item in parse_api_response(response)
        ]

    @add_auth_token_to_kwargs_from_env
    def get_by_id(self, id, **kwargs):
        url = "/%s/%s" % (self.resource.get_url_path_name(), id)
        response = self.client.get(url, **kwargs)
        if response.status_code == http_client.NOT_FOUND:
            return None
        if response.status_code != http_client.OK:
            self.handle_error(response)

        return self.resource.deserialize(parse_api_response(response=response))

    @add_auth_token_to_kwargs_from_env
    def get_property(self, id_, property_name, self_deserialize=True, **kwargs):
        """
        Gets a property of a Resource.
        id_ : Id of the resource
        property_name: Name of the property
        self_deserialize: #Implies use the deserialize method implemented by this resource.
        """
        token = kwargs.pop("token", None)
        api_key = kwargs.pop("api_key", None)

        if kwargs:
            url = "/%s/%s/%s/?%s" % (
                self.resource.get_url_path_name(),
                id_,
                property_name,
                urllib.parse.urlencode(kwargs),
            )
        else:
            url = "/%s/%s/%s/" % (self.resource.get_url_path_name(), id_, property_name)

        if token:
            response = self.client.get(url, token=token)
        elif api_key:
            response = self.client.get(url, api_key=api_key)
        else:
            response = self.client.get(url)

        if response.status_code == http_client.NOT_FOUND:
            return None
        if response.status_code != http_client.OK:
            self.handle_error(response)

        if self_deserialize:
            return [
                self.resource.deserialize(item) for item in parse_api_response(response)
            ]
        else:
            return parse_api_response(response)

    @add_auth_token_to_kwargs_from_env
    def get_by_ref_or_id(self, ref_or_id, **kwargs):
        return self.get_by_id(id=ref_or_id, **kwargs)

    def _query_details(self, **kwargs):
        if not kwargs:
            raise Exception("Query parameter is not provided.")

        token = kwargs.get("token", None)
        api_key = kwargs.get("api_key", None)
        params = kwargs.get("params", {})

        for k, v in six.iteritems(kwargs):
            # Note: That's a special case to support api_key and token kwargs
            if k not in ["token", "api_key", "params"]:
                params[k] = v

        url = "/%s/?%s" % (
            self.resource.get_url_path_name(),
            urllib.parse.urlencode(params),
        )

        if token:
            response = self.client.get(url, token=token)
        elif api_key:
            response = self.client.get(url, api_key=api_key)
        else:
            response = self.client.get(url)

        if response.status_code == http_client.NOT_FOUND:
            # for query and query_with_count
            return [], None
        if response.status_code != http_client.OK:
            self.handle_error(response)
        items = parse_api_response(response)
        instances = [self.resource.deserialize(item) for item in items]
        return instances, response

    @add_auth_token_to_kwargs_from_env
    def query(self, **kwargs):
        instances, _ = self._query_details(**kwargs)
        return instances

    @add_auth_token_to_kwargs_from_env
    def query_with_count(self, **kwargs):
        instances, response = self._query_details(**kwargs)
        if response and "X-Total-Count" in response.headers:
            return (instances, int(response.headers["X-Total-Count"]))
        else:
            return (instances, None)

    @add_auth_token_to_kwargs_from_env
    def get_by_name(self, name, **kwargs):
        instances = self.query(name=name, **kwargs)
        if not instances:
            return None
        else:
            if len(instances) > 1:
                raise Exception(
                    'More than one %s named "%s" are found.'
                    % (self.resource.__name__.lower(), name)
                )
            return instances[0]

    @add_auth_token_to_kwargs_from_env
    def create(self, instance, **kwargs):
        url = "/%s" % self.resource.get_url_path_name()
        response = self.client.post(url, instance.serialize(), **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)
        instance = self.resource.deserialize(parse_api_response(response))
        return instance

    @add_auth_token_to_kwargs_from_env
    def update(self, instance, **kwargs):
        url = "/%s/%s" % (self.resource.get_url_path_name(), instance.id)
        response = self.client.put(url, instance.serialize(), **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)
        instance = self.resource.deserialize(parse_api_response(response))
        return instance

    @add_auth_token_to_kwargs_from_env
    def delete(self, instance, **kwargs):
        url = "/%s/%s" % (self.resource.get_url_path_name(), instance.id)
        response = self.client.delete(url, **kwargs)

        if response.status_code not in [
            http_client.OK,
            http_client.NO_CONTENT,
            http_client.NOT_FOUND,
        ]:
            self.handle_error(response)
            return False

        return True

    @add_auth_token_to_kwargs_from_env
    def delete_action(self, instance, remove_files, **kwargs):
        url = "/%s/%s" % (self.resource.get_url_path_name(), instance.id)
        payload = {"remove_files": remove_files}
        response = self.client.delete(url, data=orjson.dumps(payload), **kwargs)
        if response.status_code not in [
            http_client.OK,
            http_client.NO_CONTENT,
            http_client.NOT_FOUND,
        ]:
            self.handle_error(response)
            return False

        return True

    @add_auth_token_to_kwargs_from_env
    def clone(
        self,
        source_ref,
        dest_pack,
        dest_action,
        overwrite,
        **kwargs,
    ):
        url = "/%s/%s/clone" % (self.resource.get_url_path_name(), source_ref)
        payload = {
            "dest_pack": dest_pack,
            "dest_action": dest_action,
            "overwrite": overwrite,
        }
        response = self.client.post(url, payload, **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)
        instance = self.resource.deserialize(parse_api_response(response))
        return instance

    @add_auth_token_to_kwargs_from_env
    def delete_by_id(self, instance_id, **kwargs):
        url = "/%s/%s" % (self.resource.get_url_path_name(), instance_id)
        response = self.client.delete(url, **kwargs)
        if response.status_code not in [
            http_client.OK,
            http_client.NO_CONTENT,
            http_client.NOT_FOUND,
        ]:
            self.handle_error(response)
            return False
        try:
            resp_json = parse_api_response(response)
            if resp_json:
                return resp_json
        except Exception as e:
            print(
                "\nUnable to retrieve detailed message "
                "from the HTTP response. %s\n" % six.text_type(e)
            )
        return True


class ActionAliasResourceManager(ResourceManager):
    @add_auth_token_to_kwargs_from_env
    def match(self, instance, **kwargs):
        url = "/%s/match" % self.resource.get_url_path_name()
        response = self.client.post(url, instance.serialize(), **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)
        match = parse_api_response(response)
        return (
            self.resource.deserialize(match["actionalias"]),
            match["representation"],
        )


class ActionAliasExecutionManager(ResourceManager):
    @add_auth_token_to_kwargs_from_env
    def match_and_execute(self, instance, **kwargs):
        url = "/%s/match_and_execute" % self.resource.get_url_path_name()
        response = self.client.post(url, instance.serialize(), **kwargs)

        if response.status_code != http_client.OK:
            self.handle_error(response)
        instance = self.resource.deserialize(parse_api_response(response)["results"][0])
        return instance


class ActionResourceManager(ResourceManager):
    @add_auth_token_to_kwargs_from_env
    def get_entrypoint(self, ref_or_id, **kwargs):
        url = "/%s/views/entry_point/%s" % (
            self.resource.get_url_path_name(),
            ref_or_id,
        )

        response = self.client.get(url, **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)

        return response.text


class ExecutionResourceManager(ResourceManager):
    @add_auth_token_to_kwargs_from_env
    def re_run(
        self,
        execution_id,
        parameters=None,
        tasks=None,
        no_reset=None,
        delay=0,
        **kwargs,
    ):
        url = "/%s/%s/re_run" % (self.resource.get_url_path_name(), execution_id)

        tasks = tasks or []
        no_reset = no_reset or []

        if list(set(no_reset) - set(tasks)):
            raise ValueError(
                "List of tasks to reset does not match the tasks to rerun."
            )

        data = {
            "parameters": parameters or {},
            "tasks": tasks,
            "reset": list(set(tasks) - set(no_reset)),
            "delay": delay,
        }

        response = self.client.post(url, data, **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)

        instance = self.resource.deserialize(parse_api_response(response))
        return instance

    @add_auth_token_to_kwargs_from_env
    def get_output(self, execution_id, output_type=None, **kwargs):
        url = "/%s/%s/output" % (self.resource.get_url_path_name(), execution_id)

        if output_type:
            url += "?" + urllib.parse.urlencode({"output_type": output_type})

        response = self.client.get(url, **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)

        return response.text

    @add_auth_token_to_kwargs_from_env
    def pause(self, execution_id, **kwargs):
        url = "/%s/%s" % (self.resource.get_url_path_name(), execution_id)
        data = {"status": "pausing"}

        response = self.client.put(url, data, **kwargs)

        if response.status_code != http_client.OK:
            self.handle_error(response)

        return self.resource.deserialize(parse_api_response(response))

    @add_auth_token_to_kwargs_from_env
    def resume(self, execution_id, **kwargs):
        url = "/%s/%s" % (self.resource.get_url_path_name(), execution_id)
        data = {"status": "resuming"}

        response = self.client.put(url, data, **kwargs)

        if response.status_code != http_client.OK:
            self.handle_error(response)

        return self.resource.deserialize(parse_api_response(response))

    @add_auth_token_to_kwargs_from_env
    def get_children(self, execution_id, **kwargs):
        url = "/%s/%s/children" % (self.resource.get_url_path_name(), execution_id)

        depth = kwargs.pop("depth", -1)

        params = kwargs.pop("params", {})

        if depth:
            params["depth"] = depth

        response = self.client.get(url=url, params=params, **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)
        return [
            self.resource.deserialize(item) for item in parse_api_response(response)
        ]


class InquiryResourceManager(ResourceManager):
    @add_auth_token_to_kwargs_from_env
    def respond(self, inquiry_id, inquiry_response, **kwargs):
        """
        Update st2.inquiry.respond action
        Update st2client respond command to use this?
        """
        url = "/%s/%s" % (self.resource.get_url_path_name(), inquiry_id)

        payload = {"id": inquiry_id, "response": inquiry_response}

        response = self.client.put(url, payload, **kwargs)

        if response.status_code != http_client.OK:
            self.handle_error(response)

        return self.resource.deserialize(parse_api_response(response))


class TriggerInstanceResourceManager(ResourceManager):
    @add_auth_token_to_kwargs_from_env
    def re_emit(self, trigger_instance_id, **kwargs):
        url = "/%s/%s/re_emit" % (
            self.resource.get_url_path_name(),
            trigger_instance_id,
        )
        response = self.client.post(url, None, **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)
        return parse_api_response(response)


class AsyncRequest(Resource):
    pass


class PackResourceManager(ResourceManager):
    @add_auth_token_to_kwargs_from_env
    def install(self, packs, force=False, skip_dependencies=False, **kwargs):
        url = "/%s/install" % (self.resource.get_url_path_name())
        payload = {
            "packs": packs,
            "force": force,
            "skip_dependencies": skip_dependencies,
        }
        response = self.client.post(url, payload, **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)
        instance = AsyncRequest.deserialize(parse_api_response(response))
        return instance

    @add_auth_token_to_kwargs_from_env
    def remove(self, packs, **kwargs):
        url = "/%s/uninstall" % (self.resource.get_url_path_name())
        response = self.client.post(url, {"packs": packs}, **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)
        instance = AsyncRequest.deserialize(parse_api_response(response))
        return instance

    @add_auth_token_to_kwargs_from_env
    def search(self, args, ignore_errors=False, **kwargs):
        url = "/%s/index/search" % (self.resource.get_url_path_name())
        if "query" in vars(args):
            payload = {"query": args.query}
        else:
            payload = {"pack": args.pack}

        response = self.client.post(url, payload, **kwargs)

        if response.status_code != http_client.OK:
            if ignore_errors:
                return None

            self.handle_error(response)
        data = parse_api_response(response)
        if isinstance(data, list):
            return [self.resource.deserialize(item) for item in data]
        else:
            return self.resource.deserialize(data) if data else None

    @add_auth_token_to_kwargs_from_env
    def register(self, packs=None, types=None, **kwargs):
        url = "/%s/register" % (self.resource.get_url_path_name())
        payload = {}
        if types:
            payload["types"] = types
        if packs:
            payload["packs"] = packs
        response = self.client.post(url, payload, **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)
        instance = self.resource.deserialize(parse_api_response(response))
        return instance


class ConfigManager(ResourceManager):
    @add_auth_token_to_kwargs_from_env
    def update(self, instance, **kwargs):
        url = "/%s/%s" % (self.resource.get_url_path_name(), instance.pack)
        response = self.client.put(url, instance.values, **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)
        instance = self.resource.deserialize(parse_api_response(response))
        return instance


class WebhookManager(ResourceManager):
    @add_auth_token_to_kwargs_from_env
    def post_generic_webhook(self, trigger, payload=None, trace_tag=None, **kwargs):
        url = "/webhooks/st2"

        headers = {}
        data = {"trigger": trigger, "payload": payload or {}}

        if trace_tag:
            headers["St2-Trace-Tag"] = trace_tag

        response = self.client.post(url, data=data, headers=headers, **kwargs)

        if response.status_code != http_client.OK:
            self.handle_error(response)

        return parse_api_response(response)

    @add_auth_token_to_kwargs_from_env
    def match(self, instance, **kwargs):
        url = "/%s/match" % self.resource.get_url_path_name()
        response = self.client.post(url, instance.serialize(), **kwargs)
        if response.status_code != http_client.OK:
            self.handle_error(response)
        match = parse_api_response(response)
        return (
            self.resource.deserialize(match["actionalias"]),
            match["representation"],
        )


class StreamManager(ResourceManager):
    def __init__(self, endpoint, cacert=None, debug=False, basic_auth=None):
        super(StreamManager, self).__init__(
            resource=None,
            endpoint=endpoint,
            cacert=cacert,
            debug=debug,
            basic_auth=basic_auth,
        )
        self._url = httpclient.get_url_without_trailing_slash(endpoint) + "/stream"

    @add_auth_token_to_kwargs_from_env
    def listen(self, events=None, **kwargs):
        # Late import to avoid very expensive in-direct import (~1 second) when this function is
        # not called / used
        from sseclient import SSEClient

        url = self._url
        query_params = {}
        request_params = {}

        if events and isinstance(events, six.string_types):
            events = [events]

        if "token" in kwargs:
            query_params["x-auth-token"] = kwargs.get("token")

        if "api_key" in kwargs:
            query_params["st2-api-key"] = kwargs.get("api_key")

        if "end_event" in kwargs:
            query_params["end_event"] = kwargs.get("end_event")

        if "end_execution_id" in kwargs:
            query_params["end_execution_id"] = kwargs.get("end_execution_id")

        if events:
            query_params["events"] = ",".join(events)

        if self.cacert is not None:
            request_params["verify"] = self.cacert

        if self.basic_auth:
            request_params["auth"] = self.basic_auth

        query_string = "?" + urllib.parse.urlencode(query_params)
        url = url + query_string

        response = requests.get(url, stream=True, **request_params)
        client = SSEClient(response)

        for message in client.events():
            # If the execution on the API server takes too long, the message
            # can be empty. In this case, rerun the query.
            if not message.data:
                continue
            yield orjson.loads(message.data)


class WorkflowManager(object):
    def __init__(self, endpoint, cacert, debug, basic_auth=None):
        self.debug = debug
        self.cacert = cacert
        self.endpoint = endpoint + "/workflows"
        self.client = httpclient.HTTPClient(
            root=self.endpoint, cacert=cacert, debug=debug, basic_auth=basic_auth
        )

    @staticmethod
    def handle_error(response):
        try:
            content = parse_api_response(response)
            fault = content.get("faultstring", "") if content else ""

            if fault:
                response.reason += "\nMESSAGE: %s" % fault
        except Exception as e:
            response.reason += (
                "\nUnable to retrieve detailed message "
                "from the HTTP response. %s\n" % six.text_type(e)
            )

        response.raise_for_status()

    @add_auth_token_to_kwargs_from_env
    def inspect(self, definition, **kwargs):
        url = "/inspect"

        if not isinstance(definition, six.string_types):
            raise TypeError(
                f"Workflow definition is not type of string (was {type(definition)})."
            )

        if "headers" not in kwargs:
            kwargs["headers"] = {}

        kwargs["headers"]["content-type"] = "text/plain"

        response = self.client.post_raw(url, definition, **kwargs)

        if response.status_code != http_client.OK:
            self.handle_error(response)

        return parse_api_response(response)


class ServiceRegistryGroupsManager(ResourceManager):
    @add_auth_token_to_kwargs_from_env
    def list(self, **kwargs):
        url = "/service_registry/groups"

        headers = {}
        response = self.client.get(url, headers=headers, **kwargs)

        if response.status_code != http_client.OK:
            self.handle_error(response)

        groups = parse_api_response(response)["groups"]

        result = []
        for group in groups:
            item = self.resource.deserialize({"group_id": group})
            result.append(item)

        return result


class ServiceRegistryMembersManager(ResourceManager):
    @add_auth_token_to_kwargs_from_env
    def list(self, group_id, **kwargs):
        url = "/service_registry/groups/%s/members" % (group_id)

        headers = {}
        response = self.client.get(url, headers=headers, **kwargs)

        if response.status_code != http_client.OK:
            self.handle_error(response)

        members = parse_api_response(response)["members"]

        result = []
        for member in members:
            data = {
                "group_id": group_id,
                "member_id": member["member_id"],
                "capabilities": member["capabilities"],
            }
            item = self.resource.deserialize(data)
            result.append(item)

        return result


class KeyValuePairResourceManager(ResourceManager):
    @add_auth_token_to_kwargs_from_env
    def get_by_name(self, name, **kwargs):

        token = kwargs.get("token", None)
        api_key = kwargs.get("api_key", None)
        params = kwargs.get("params", {})

        for k, v in six.iteritems(kwargs):
            # Note: That's a special case to support api_key and token kwargs
            if k not in ["token", "api_key", "params"]:
                params[k] = v

        url = "/%s/%s/?%s" % (
            self.resource.get_url_path_name(),
            name,
            urllib.parse.urlencode(params),
        )

        if token:
            response = self.client.get(url, token=token)
        elif api_key:
            response = self.client.get(url, api_key=api_key)
        else:
            response = self.client.get(url)

        if response.status_code == http_client.NOT_FOUND:
            # for query and query_with_count
            return []
        if response.status_code != http_client.OK:
            self.handle_error(response)

        return self.resource.deserialize(parse_api_response(response))
