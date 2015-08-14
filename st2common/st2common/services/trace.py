# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mongoengine import ValidationError

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.exceptions.trace import UniqueTraceNotFoundException
from st2common.models.api.trace import TraceContext
from st2common.models.db.trace import TraceDB, TraceComponentDB
from st2common.persistence.trace import Trace

LOG = logging.getLogger(__name__)

__all__ = [
    'get_trace_db_by_action_execution',
    'get_trace_db_by_rule',
    'get_trace_db_by_trigger_instance',
    'get_trace',
    'add_or_update_given_trace_context',
    'add_or_update_given_trace_db'
]


def _get_valid_trace_context(trace_context):
    """
    Check if tarce_context is a valid type and returns a TraceContext object.
    """
    assert isinstance(trace_context, (TraceContext, dict))

    # Pretty much abuse the dynamic nature of python to make it possible to support
    # both dict and TraceContext types.
    if isinstance(trace_context, dict):
        trace_context = TraceContext(**trace_context)

    return trace_context


def _get_single_trace_by_component(**component_filter):
    """
    Tries to return a single Trace mathing component_filter. Raises an exception
    when a filter matches multiple.
    """
    traces = Trace.query(**component_filter)
    if len(traces) == 0:
        return None
    elif len(traces) > 1:
        raise UniqueTraceNotFoundException(
            'More than 1 trace matching %s found.' % component_filter)
    return traces[0]


def get_trace_db_by_action_execution(action_execution):
    return _get_single_trace_by_component(action_executions__object_id=str(action_execution.id))


def get_trace_db_by_rule(rule):
    # by rule could return multiple traces
    return Trace.query(rules__object_id=str(rule.id))


def get_trace_db_by_trigger_instance(trigger_instance):
    return _get_single_trace_by_component(trigger_instances__object_id=str(trigger_instance.id))


def get_trace(trace_context, ignore_trace_id=False):
    """
    :param trace_context: context object using which a trace can be found.
    :type trace_context: ``dict`` or ``TraceContext``

    :param ignore_trace_id: Even if a trace_id is provided will be ignored.
    :type ignore_trace_id: ``str``

    :rtype: ``TraceDB``
    """

    trace_context = _get_valid_trace_context(trace_context)

    if not trace_context.id_ and not trace_context.trace_id:
        raise ValueError('Atleast one of id_ or trace_id should be specified.')

    if trace_context.id_:
        try:
            return Trace.get_by_id(trace_context.id_)
        except (ValidationError, ValueError):
            LOG.warning('Database lookup for Trace with id="%s" failed.',
                        trace_context.id_, exc_info=True)
            raise StackStormDBObjectNotFoundError(
                'Unable to find Trace with id="%s"' % trace_context.id_)

    if ignore_trace_id:
        return None

    traces = Trace.query(trace_id=trace_context.trace_id)

    # Assume this method only handles 1 trace.
    if len(traces) > 1:
        raise UniqueTraceNotFoundException(
            'More than 1 Trace matching %s found.' % trace_context.trace_id)

    return traces[0]


def add_or_update_given_trace_context(trace_context, action_executions=None, rules=None,
                                      trigger_instances=None):
    """
    Will update an existing Trace or add a new Trace. This method will only look for exact
    Trace as identified by the trace_context. Even if the trace_context contain a trace_id
    it shall not be used to lookup a Trace.

    * If an exact matching Trace is not found a new Trace is created
    * Whenever only a trace_id is supplied a new Trace is created.

    :param trace_context: context object using which a trace can be found. If not found
                          trace_context.trace_id is used to start new trace.
    :type trace_context: ``dict`` or ``TraceContext``

    :param action_executions: The action_execution to be added to the Trace. Should a list
                              of object_ids.
    :type action_executions: ``list``

    :param rules: The rules to be added to the Trace. Should a list of object_ids.
    :type rules: ``list``

    :param trigger_instances: The trigger_instances to be added to the Trace. Should a list
                              of object_ids.
    :type trigger_instances: ``list``

    :rtype: ``TraceDB``
    """
    trace_db = get_trace(trace_context=trace_context, ignore_trace_id=True)
    if not trace_db:
        # since trace_db is None need to end up with a valid trace_context
        trace_context = _get_valid_trace_context(trace_context)
        trace_db = TraceDB(trace_id=trace_context.trace_id)
    return add_or_update_given_trace_db(trace_db=trace_db,
                                        action_executions=action_executions,
                                        rules=rules,
                                        trigger_instances=trigger_instances)


def add_or_update_given_trace_db(trace_db, action_executions=None, rules=None,
                                 trigger_instances=None):
    """
    Will update an existing Trace.

    :param trace_db: The TraceDB to update.
    :type trace_db: ``TraceDB``

    :param action_executions: The action_execution to be added to the Trace. Should a list
                              of object_ids.
    :type action_executions: ``list``

    :param rules: The rules to be added to the Trace. Should a list of object_ids.
    :type rules: ``list``

    :param trigger_instances: The trigger_instances to be added to the Trace. Should a list
                              of object_ids.
    :type trigger_instances: ``list``

    :rtype: ``TraceDB``
    """
    if trace_db is None:
        raise ValueError('trace_db should be non-None.')

    if not action_executions:
        action_executions = []
    action_executions = [TraceComponentDB(object_id=action_execution)
                         for action_execution in action_executions]
    if trace_db.action_executions:
        action_executions.extend(trace_db.action_executions)

    if not rules:
        rules = []
    rules = [TraceComponentDB(object_id=rule) for rule in rules]
    if trace_db.rules:
        rules.extend(trace_db.rules)

    if not trigger_instances:
        trigger_instances = []
    trigger_instances = [TraceComponentDB(object_id=trigger_instance)
                         for trigger_instance in trigger_instances]
    if trace_db.trigger_instances:
        trigger_instances.extend(trace_db.trigger_instances)

    trace_db.action_executions = action_executions
    trace_db.rules = rules
    trace_db.trigger_instances = trigger_instances

    return Trace.add_or_update(trace_db)
