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

import itertools

import six

from st2api.controllers.resource import ResourceController
from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.models.db.execution import ActionExecutionOutputDB
from st2common.models.api.execution import ActionExecutionAPI
from st2common.models.api.execution import ActionExecutionOutputAPI
from st2common.persistence.execution import ActionExecution
from st2common.persistence.execution import ActionExecutionOutput
from st2common.router import Response
from st2common.util.jsonify import json_encode
from st2common.rbac.types import PermissionType
from st2common.stream.listener import get_listener

__all__ = ["ActionExecutionOutputStreamController"]

LOG = logging.getLogger(__name__)

# Event which is returned when no more data will be produced on this stream endpoint before closing
# the connection.
NO_MORE_DATA_EVENT = "event: EOF\ndata: ''\n\n"


class ActionExecutionOutputStreamController(ResourceController):
    model = ActionExecutionAPI
    access = ActionExecution

    supported_filters = {"output_type": "output_type"}

    CLOSE_STREAM_LIVEACTION_STATES = action_constants.LIVEACTION_COMPLETED_STATES + [
        action_constants.LIVEACTION_STATUS_PAUSING,
        action_constants.LIVEACTION_STATUS_RESUMING,
    ]

    def get_one(self, id, output_type="all", requester_user=None):
        # Special case for id == "last"
        if id == "last":
            execution_db = ActionExecution.query().order_by("-id").limit(1).first()

            if not execution_db:
                raise ValueError("No executions found in the database")

            id = str(execution_db.id)

        execution_db = self._get_one_by_id(
            id=id,
            requester_user=requester_user,
            permission_type=PermissionType.EXECUTION_VIEW,
        )
        execution_id = str(execution_db.id)

        query_filters = {}
        if output_type and output_type != "all":
            query_filters["output_type"] = output_type

        def format_output_object(output_db_or_api):
            if isinstance(output_db_or_api, ActionExecutionOutputDB):
                data = ActionExecutionOutputAPI.from_model(output_db_or_api)
            elif isinstance(output_db_or_api, ActionExecutionOutputAPI):
                data = output_db_or_api
            else:
                raise ValueError("Unsupported format: %s" % (type(output_db_or_api)))

            event = "st2.execution.output__create"
            result = "event: %s\ndata: %s\n\n" % (event, json_encode(data, indent=None))
            return result

        def existing_output_iter():
            # Consume and return all of the existing lines
            output_dbs = ActionExecutionOutput.query(
                execution_id=execution_id, **query_filters
            )

            # Note: We return all at once instead of yield line by line to avoid multiple socket
            # writes and to achieve better performance
            output = [format_output_object(output_db) for output_db in output_dbs]
            output = "".join(output)
            yield six.binary_type(output.encode("utf-8"))

        def new_output_iter():
            def noop_gen():
                yield six.binary_type(NO_MORE_DATA_EVENT.encode("utf-8"))

            # Bail out if execution has already completed / been paused
            if execution_db.status in self.CLOSE_STREAM_LIVEACTION_STATES:
                return noop_gen()

            # Wait for and return any new line which may come in
            execution_ids = [execution_id]
            listener = get_listener(
                name="execution_output"
            )  # pylint: disable=no-member
            gen = listener.generator(execution_ids=execution_ids)

            def format(gen):
                for pack in gen:
                    if not pack:
                        continue
                    else:
                        (_, model_api) = pack

                        # Note: gunicorn wsgi handler expect bytes, not unicode
                        # pylint: disable=no-member
                        if isinstance(model_api, ActionExecutionOutputAPI):
                            if (
                                output_type
                                and output_type != "all"
                                and model_api.output_type != output_type
                            ):
                                continue

                            output = format_output_object(model_api).encode("utf-8")
                            yield six.binary_type(output)
                        elif isinstance(model_api, ActionExecutionAPI):
                            if model_api.status in self.CLOSE_STREAM_LIVEACTION_STATES:
                                yield six.binary_type(
                                    NO_MORE_DATA_EVENT.encode("utf-8")
                                )
                                break
                        else:
                            LOG.debug("Unrecognized message type: %s" % (model_api))

            gen = format(gen)
            return gen

        def make_response():
            app_iter = itertools.chain(existing_output_iter(), new_output_iter())
            res = Response(
                headerlist=[
                    ("X-Accel-Buffering", "no"),
                    ("Cache-Control", "no-cache"),
                    ("Content-Type", "text/event-stream; charset=UTF-8"),
                ],
                app_iter=app_iter,
            )
            return res

        res = make_response()
        return res


action_execution_output_controller = ActionExecutionOutputStreamController()
