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
from oslo_config import cfg
from bson.objectid import ObjectId

from st2common import log as logging
from st2common.util import date as date_utils
from st2common.util import reference
import st2common.util.action_db as action_utils
from st2common.constants import action as action_constants
from st2common.persistence.execution import ActionExecution
from st2common.persistence.runner import RunnerType
from st2common.persistence.rule import Rule
from st2common.persistence.trigger import TriggerType, Trigger, TriggerInstance
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, LiveActionAPI
from st2common.models.api.rule import RuleAPI
from st2common.models.api.trigger import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI
from st2common.models.db.execution import ActionExecutionDB
from st2common.runners import utils as runners_utils
from st2common.metrics.base import Timer
from st2common.services import coordination
from six.moves import range


__all__ = [
    "create_execution_object",
    "update_execution",
    "abandon_execution_if_incomplete",
    "is_execution_canceled",
    "AscendingSortedDescendantView",
    "DFSDescendantView",
    "get_descendants",
]

LOG = logging.getLogger(__name__)

# Attributes which are stored in the "liveaction" dictionary when composing LiveActionDB object
# into a ActionExecution compatible dictionary.
# Those attributes are LiveAction specific and are therefore stored in a "liveaction" key
LIVEACTION_ATTRIBUTES = [
    "id",
    "callback",
    "action",
    "action_is_workflow",
    "runner_info",
    "parameters",
    "notify",
]


def _decompose_liveaction(liveaction_db):
    """
    Splits the liveaction into an ActionExecution compatible dict.
    """
    decomposed = {"liveaction": {}}
    liveaction_api = vars(LiveActionAPI.from_model(liveaction_db))
    for k in liveaction_api.keys():
        if k in LIVEACTION_ATTRIBUTES:
            decomposed["liveaction"][k] = liveaction_api[k]
        else:
            decomposed[k] = getattr(liveaction_db, k)
    return decomposed


def _create_execution_log_entry(status, timestamp=None):
    """
    Create execution log entry object for the provided execution status.
    """
    return {
        "timestamp": timestamp or date_utils.get_datetime_utc_now(),
        "status": status,
    }


def create_execution_object(
    liveaction, action_db=None, runnertype_db=None, publish=True
):
    if not action_db:
        action_db = action_utils.get_action_by_ref(liveaction.action)

    if not runnertype_db:
        runnertype_db = RunnerType.get_by_name(action_db.runner_type["name"])

    attrs = {
        "action": vars(ActionAPI.from_model(action_db)),
        "parameters": liveaction["parameters"],
        "runner": vars(RunnerTypeAPI.from_model(runnertype_db)),
    }
    attrs.update(_decompose_liveaction(liveaction))

    if "rule" in liveaction.context:
        rule = reference.get_model_from_ref(Rule, liveaction.context.get("rule", {}))
        attrs["rule"] = vars(RuleAPI.from_model(rule))

    if "trigger_instance" in liveaction.context:
        trigger_instance_id = liveaction.context.get("trigger_instance", {})
        trigger_instance_id = trigger_instance_id.get("id", None)
        trigger_instance = TriggerInstance.get_by_id(trigger_instance_id)
        trigger = reference.get_model_by_resource_ref(
            db_api=Trigger, ref=trigger_instance.trigger
        )
        trigger_type = reference.get_model_by_resource_ref(
            db_api=TriggerType, ref=trigger.type
        )
        trigger_instance = reference.get_model_from_ref(
            TriggerInstance, liveaction.context.get("trigger_instance", {})
        )
        attrs["trigger_instance"] = vars(
            TriggerInstanceAPI.from_model(trigger_instance)
        )
        attrs["trigger"] = vars(TriggerAPI.from_model(trigger))
        attrs["trigger_type"] = vars(TriggerTypeAPI.from_model(trigger_type))

    parent = _get_parent_execution(liveaction)
    if parent:
        attrs["parent"] = str(parent.id)

    attrs["log"] = [_create_execution_log_entry(liveaction["status"])]

    # TODO: This object initialization takes 20-30or so ms
    execution = ActionExecutionDB(**attrs)
    # TODO: Do 100% research this is fully safe and unique in distributed setups
    execution.id = ObjectId()
    execution.web_url = _get_web_url_for_execution(str(execution.id))

    # NOTE: User input data is already validate as part of the API request,
    # other data is set by us. Skipping validation here makes operation 10%-30% faster
    execution = ActionExecution.add_or_update(
        execution, publish=publish, validate=False
    )

    if parent and str(execution.id) not in parent.children:
        values = {}
        values["push__children"] = str(execution.id)
        ActionExecution.update(parent, **values)

    return execution


def _get_parent_execution(child_liveaction_db):
    parent_execution_id = child_liveaction_db.context.get("parent", {}).get(
        "execution_id", None
    )

    if parent_execution_id:
        try:
            return ActionExecution.get_by_id(parent_execution_id)
        except:
            LOG.exception(
                "No valid execution object found in db for id: %s" % parent_execution_id
            )
            return None

    return None


def _get_web_url_for_execution(execution_id):
    base_url = cfg.CONF.webui.webui_base_url
    return "%s/#/history/%s/general" % (base_url, execution_id)


def update_execution(liveaction_db, publish=True, set_result_size=False):
    """
    :param set_result_size: True to calculate size of the serialized result field value and set it
                            on the "result_size" database field.
    """
    execution = ActionExecution.get(liveaction__id=str(liveaction_db.id))

    with coordination.get_coordinator().get_lock(str(liveaction_db.id).encode()):
        # Skip execution object update when action is already in completed state.
        if execution.status in action_constants.LIVEACTION_COMPLETED_STATES:
            LOG.debug(
                "[%s] Action is already in completed state: %s. Skipping execution update to state: %s."
                % (execution.id, execution.status, liveaction_db.status)
            )
            return execution

        decomposed = _decompose_liveaction(liveaction_db)

        kw = {}
        for k, v in six.iteritems(decomposed):
            kw["set__" + k] = v

        if liveaction_db.status != execution.status:
            # Note: If the status changes we store this transition in the "log" attribute of action
            # execution
            kw["push__log"] = _create_execution_log_entry(liveaction_db.status)

        if set_result_size:
            # Sadly with the current ORM abstraction there is no better way to achieve updating
            # result_size and we need to serialize the value again - luckily that operation is fast.
            # To put things into perspective - on 4 MB result dictionary it only takes 7 ms which is
            # negligible compared to other DB operations duration (and for smaller results it takes
            # in sub ms range).
            with Timer(key="action.executions.calculate_result_size"):
                result_size = len(
                    ActionExecutionDB.result._serialize_field_value(
                        liveaction_db.result
                    )
                )
                kw["set__result_size"] = result_size

        execution = ActionExecution.update(execution, publish=publish, **kw)
        return execution


def abandon_execution_if_incomplete(liveaction_id, publish=True):
    """
    Marks execution as abandoned if it is still incomplete. Abandoning an
    execution implies that its end state is unknown and cannot anylonger
    be determined. This method should only be called if the owning process
    is certain it can no longer determine status of an execution.
    """
    liveaction_db = action_utils.get_liveaction_by_id(liveaction_id)

    # No need to abandon and already complete action
    if liveaction_db.status in action_constants.LIVEACTION_COMPLETED_STATES:
        raise ValueError(
            "LiveAction %s already in a completed state %s."
            % (liveaction_id, liveaction_db.status)
        )

    # Update status to reflect execution being abandoned.
    liveaction_db = action_utils.update_liveaction_status(
        status=action_constants.LIVEACTION_STATUS_ABANDONED,
        liveaction_db=liveaction_db,
        result={},
    )

    execution_db = update_execution(liveaction_db, publish=publish)

    LOG.info(
        "Marked execution %s as %s.",
        execution_db.id,
        action_constants.LIVEACTION_STATUS_ABANDONED,
    )

    # Invoke post run on the action to execute post run operations such as callback.
    runners_utils.invoke_post_run(liveaction_db)

    return execution_db


def is_execution_canceled(execution_id):
    try:
        execution = ActionExecution.get_by_id(execution_id)
        return execution.status == action_constants.LIVEACTION_STATUS_CANCELED
    except:
        return False  # XXX: What to do here?


def get_parent_context(liveaction_db):
    """
    Returns context of the parent execution.

    :return: If found the parent context else None.
    :rtype: dict
    """
    context = getattr(liveaction_db, "context", None)
    if not context:
        return None
    return context.get("parent", None)


class AscendingSortedDescendantView(object):
    def __init__(self):
        self._result = []

    def add(self, child):
        self._result.append(child)

    @property
    def result(self):
        return sorted(self._result, key=lambda execution: execution.start_timestamp)


class DFSDescendantView(object):
    def __init__(self):
        self._result = []

    def add(self, child):
        self._result.append(child)

    @property
    def result(self):
        return self._result


DESCENDANT_VIEWS = {
    "sorted": AscendingSortedDescendantView,
    "default": DFSDescendantView,
}


def get_descendants(actionexecution_id, descendant_depth=-1, result_fmt=None):
    """
    Returns all descendant executions upto the specified descendant_depth for
    the supplied actionexecution_id.
    """
    descendants = DESCENDANT_VIEWS.get(result_fmt, DFSDescendantView)()
    children = ActionExecution.query(
        parent=actionexecution_id, **{"order_by": ["start_timestamp"]}
    )
    LOG.debug("Found %s children for id %s.", len(children), actionexecution_id)
    current_level = [(child, 1) for child in children]

    while current_level:
        parent, level = current_level.pop(0)
        parent_id = str(parent.id)
        descendants.add(parent)
        if not parent.children:
            continue
        if level != -1 and level == descendant_depth:
            continue
        children = ActionExecution.query(
            parent=parent_id, **{"order_by": ["start_timestamp"]}
        )
        LOG.debug("Found %s children for id %s.", len(children), parent_id)
        # prepend for DFS
        for idx in range(len(children)):
            current_level.insert(idx, (children[idx], level + 1))
    return descendants.result
