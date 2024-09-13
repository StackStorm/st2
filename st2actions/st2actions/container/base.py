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

import sys
import traceback

import six
from oslo_config import cfg

from st2common import log as logging
from st2common.util import date as date_utils
from st2common.constants import action as action_constants
from st2common.content import utils as content_utils
from st2common.exceptions import actionrunner
from st2common.exceptions.param import ParamException
from st2common.models.system.action import ResolvedActionParameters
from st2common.persistence.execution import ActionExecution
from st2common.services import access, executions, queries
from st2common.util.action_db import get_action_by_ref, get_runnertype_by_name
from st2common.util.action_db import update_liveaction_status, get_liveaction_by_id
from st2common.util import param as param_utils
from st2common.util.config_loader import ContentPackConfigLoader
from st2common.metrics.base import CounterWithTimer
from st2common.metrics.base import Timer
from st2common.util import jsonify

from st2common.runners.base import get_runner
from st2common.runners.base import AsyncActionRunner, PollingAsyncActionRunner

LOG = logging.getLogger(__name__)

__all__ = ["RunnerContainer", "get_runner_container"]


class RunnerContainer(object):
    def dispatch(self, liveaction_db):
        action_db = get_action_by_ref(liveaction_db.action)
        if not action_db:
            raise Exception("Action %s not found in DB." % (liveaction_db.action))

        liveaction_db.context["pack"] = action_db.pack

        runner_type_db = get_runnertype_by_name(action_db.runner_type["name"])

        extra = {"liveaction_db": liveaction_db, "runner_type_db": runner_type_db}
        LOG.info("Dispatching Action to a runner", extra=extra)

        # Get runner instance.
        runner = self._get_runner(runner_type_db, action_db, liveaction_db)

        LOG.debug(
            'Runner instance for RunnerType "%s" is: %s', runner_type_db.name, runner
        )

        # Process the request.
        funcs = {
            action_constants.LIVEACTION_STATUS_REQUESTED: self._do_run,
            action_constants.LIVEACTION_STATUS_SCHEDULED: self._do_run,
            action_constants.LIVEACTION_STATUS_RUNNING: self._do_run,
            action_constants.LIVEACTION_STATUS_CANCELING: self._do_cancel,
            action_constants.LIVEACTION_STATUS_PAUSING: self._do_pause,
            action_constants.LIVEACTION_STATUS_RESUMING: self._do_resume,
        }

        if liveaction_db.status not in funcs:
            raise actionrunner.ActionRunnerDispatchError(
                "Action runner is unable to dispatch the liveaction because it is "
                'in an unsupported status of "%s".' % liveaction_db.status
            )

        with CounterWithTimer(key="action.executions"):
            status = liveaction_db.status
            with CounterWithTimer(key="action.executions.process.%s" % (status)):
                liveaction_db = funcs[liveaction_db.status](runner)

        return liveaction_db.result

    def _do_run(self, runner):
        # Create a temporary auth token which will be available
        # for the duration of the action execution.
        runner.auth_token = self._create_auth_token(
            context=runner.context,
            action_db=runner.action,
            liveaction_db=runner.liveaction,
        )

        try:
            # Finalized parameters are resolved and then rendered. This process could
            # fail. Handle the exception and report the error correctly.
            try:
                runner_params, action_params = param_utils.render_final_params(
                    runner.runner_type.runner_parameters,
                    runner.action.parameters,
                    runner.liveaction.parameters,
                    runner.liveaction.context,
                )

                runner.runner_parameters = runner_params
            except ParamException as e:
                raise actionrunner.ActionRunnerException(six.text_type(e))

            LOG.debug("Performing pre-run for runner: %s", runner.runner_id)
            runner.pre_run()

            # Mask secret parameters in the log context
            resolved_action_params = ResolvedActionParameters(
                action_db=runner.action,
                runner_type_db=runner.runner_type,
                runner_parameters=runner_params,
                action_parameters=action_params,
            )

            extra = {"runner": runner, "parameters": resolved_action_params}
            LOG.debug("Performing run for runner: %s" % (runner.runner_id), extra=extra)

            with CounterWithTimer(key="action.executions"):
                with CounterWithTimer(key="action.%s.executions" % (runner.action.ref)):
                    (status, result, context) = runner.run(action_params)
                    result = jsonify.try_loads(result)

            action_completed = status in action_constants.LIVEACTION_COMPLETED_STATES

            if (
                isinstance(runner, PollingAsyncActionRunner)
                and runner.is_polling_enabled()
                and not action_completed
            ):
                queries.setup_query(runner.liveaction.id, runner.runner_type, context)
        except:
            LOG.exception("Failed to run action.")
            _, ex, tb = sys.exc_info()
            # mark execution as failed.
            status = action_constants.LIVEACTION_STATUS_FAILED
            # include the error message and traceback to try and provide some hints.
            result = {
                "error": str(ex),
                "traceback": "".join(traceback.format_tb(tb, 20)),
            }
            context = None
        finally:
            # Log action completion
            extra = {"result": result, "status": status}
            LOG.debug('Action "%s" completed.' % (runner.action.name), extra=extra)

            # Update the final status of liveaction and corresponding action execution.
            with Timer(key="action.executions.update_status"):
                runner.liveaction = self._update_status(
                    runner.liveaction.id, status, result, context
                )

            # Always clean-up the auth_token
            # This method should be called in the finally block to ensure post_run is not impacted.
            self._clean_up_auth_token(runner=runner, status=status)

        LOG.debug("Performing post_run for runner: %s", runner.runner_id)
        runner.post_run(status=status, result=result)

        LOG.debug("Runner do_run result", extra={"result": runner.liveaction.result})
        LOG.audit("Liveaction completed", extra={"liveaction_db": runner.liveaction})

        return runner.liveaction

    def _do_cancel(self, runner):
        try:
            extra = {"runner": runner}
            LOG.debug(
                "Performing cancel for runner: %s", (runner.runner_id), extra=extra
            )
            (status, result, context) = runner.cancel()

            # Update the final status of liveaction and corresponding action execution.
            # The status is updated here because we want to keep the workflow running
            # as is if the cancel operation failed.
            runner.liveaction = self._update_status(
                runner.liveaction.id, status, result, context
            )
        except:
            _, ex, tb = sys.exc_info()
            # include the error message and traceback to try and provide some hints.
            result = {
                "error": str(ex),
                "traceback": "".join(traceback.format_tb(tb, 20)),
            }
            LOG.exception(
                "Failed to cancel action %s." % (runner.liveaction.id), extra=result
            )
        finally:
            # Always clean-up the auth_token
            # This method should be called in the finally block to ensure post_run is not impacted.
            self._clean_up_auth_token(runner=runner, status=runner.liveaction.status)

        LOG.debug("Performing post_run for runner: %s", runner.runner_id)
        result = {"error": "Execution canceled by user."}
        runner.post_run(status=runner.liveaction.status, result=result)

        return runner.liveaction

    def _do_pause(self, runner):
        # Initialise to avoid E0601: Use before assignment.
        status = result = context = None
        try:
            extra = {"runner": runner}
            LOG.debug(
                "Performing pause for runner: %s", (runner.runner_id), extra=extra
            )
            (status, result, context) = runner.pause()
        except:
            _, ex, tb = sys.exc_info()
            # include the error message and traceback to try and provide some hints.
            status = action_constants.LIVEACTION_STATUS_FAILED
            result = {
                "error": str(ex),
                "traceback": "".join(traceback.format_tb(tb, 20)),
            }
            context = runner.liveaction.context
            LOG.exception(
                "Failed to pause action %s." % (runner.liveaction.id), extra=result
            )
        finally:
            # Update the final status of liveaction and corresponding action execution.
            runner.liveaction = self._update_status(
                runner.liveaction.id, status, result, context
            )

            # Always clean-up the auth_token
            self._clean_up_auth_token(runner=runner, status=runner.liveaction.status)

        return runner.liveaction

    def _do_resume(self, runner):
        # Initialise to avoid E0601: Use before assignment.
        status = result = context = None
        try:
            extra = {"runner": runner}
            LOG.debug(
                "Performing resume for runner: %s", (runner.runner_id), extra=extra
            )
            (status, result, context) = runner.resume()
            result = jsonify.try_loads(result)
            action_completed = status in action_constants.LIVEACTION_COMPLETED_STATES

            if (
                isinstance(runner, PollingAsyncActionRunner)
                and runner.is_polling_enabled()
                and not action_completed
            ):
                queries.setup_query(runner.liveaction.id, runner.runner_type, context)
        except:
            _, ex, tb = sys.exc_info()
            # include the error message and traceback to try and provide some hints.
            status = action_constants.LIVEACTION_STATUS_FAILED
            result = {
                "error": str(ex),
                "traceback": "".join(traceback.format_tb(tb, 20)),
            }
            context = runner.liveaction.context
            LOG.exception(
                "Failed to resume action %s." % (runner.liveaction.id), extra=result
            )
        finally:
            # Update the final status of liveaction and corresponding action execution.
            runner.liveaction = self._update_status(
                runner.liveaction.id, status, result, context
            )

            # Always clean-up the auth_token
            # This method should be called in the finally block to ensure post_run is not impacted.
            self._clean_up_auth_token(runner=runner, status=runner.liveaction.status)

        LOG.debug("Performing post_run for runner: %s", runner.runner_id)
        runner.post_run(status=status, result=result)

        LOG.debug("Runner do_run result", extra={"result": runner.liveaction.result})
        LOG.audit("Liveaction completed", extra={"liveaction_db": runner.liveaction})

        return runner.liveaction

    def _clean_up_auth_token(self, runner, status):
        """
        Clean up the temporary auth token for the current action.

        Note: This method should never throw since it's called inside finally block which assumes
        it doesn't throw.
        """
        # Deletion of the runner generated auth token is delayed until the token expires.
        # Async actions use the auth token to launch other
        # actions in the workflow. If the auth token is deleted here, then the actions
        # in the workflow will fail with unauthorized exception.
        is_async_runner = isinstance(runner, AsyncActionRunner)
        action_completed = status in action_constants.LIVEACTION_COMPLETED_STATES

        if not is_async_runner or (is_async_runner and action_completed):
            try:
                self._delete_auth_token(runner.auth_token)
            except:
                LOG.exception("Unable to clean-up auth_token.")

            return True

        return False

    def _update_live_action_db(self, liveaction_id, status, result, context):
        """
        Update LiveActionDB object for the provided liveaction id.
        """
        liveaction_db = get_liveaction_by_id(liveaction_id)

        state_changed = (
            liveaction_db.status != status
            and liveaction_db.status not in action_constants.LIVEACTION_COMPLETED_STATES
        )

        if status in action_constants.LIVEACTION_COMPLETED_STATES:
            end_timestamp = date_utils.get_datetime_utc_now()
        else:
            end_timestamp = None

        with Timer(key="action.executions.update_liveaction_db"):
            liveaction_db = update_liveaction_status(
                status=status if state_changed else liveaction_db.status,
                result=result,
                context=context,
                end_timestamp=end_timestamp,
                liveaction_db=liveaction_db,
            )

        return (liveaction_db, state_changed)

    def _update_status(self, liveaction_id, status, result, context):
        with Timer(key="action.executions.update_liveaction_db"):
            try:
                # NOTE: The next two operations take a very long time in master with large executions
                # (long standing issue), but because start_timestamp and end_timestamp measure how long
                # it took for the runner to run the action, it doesn't include the time it took to
                # actually write results / persist execution into the database - that's a problem
                # because we have no good direct visibility into that.
                #
                # The UX user would experience is - they would run an action which produces large
                # result, CLI / API would show execution as running for a long time (until it's
                # persisted in the database), but when it will finally be written to the database,
                # duration will be shown as a short time, because it's measured based on start and
                # end timestamp.
                #
                # This mean we can have, for example, Python runner action which returns a lot of data
                # and takes only 0.5 second to finish, but next two database operations can easily take
                # 10 seconds each.
                #
                # To work around that and provide some additional visibility into that to the operators
                # and users, we update "end_timestamp" on each object again after both of them have
                # already been written. That atomic single field update is very fast and adds no
                # additional overhead.
                LOG.debug(
                    "Setting status: %s for liveaction: %s", status, liveaction_id
                )
                liveaction_db, state_changed = self._update_live_action_db(
                    liveaction_id, status, result, context
                )
            except Exception as e:
                LOG.exception(
                    "Cannot update liveaction "
                    "(id: %s, status: %s, result: %s)."
                    % (liveaction_id, status, result)
                )
                raise e

        # live_action_written_to_db_dt = date_utils.get_datetime_utc_now()

        with Timer(key="action.executions.update_execution_db"):
            try:
                executions.update_execution(
                    liveaction_db,
                    publish=state_changed,
                    set_result_size=True,
                )
                extra = {"liveaction_db": liveaction_db}
                LOG.debug("Updated liveaction after run", extra=extra)
            except Exception as e:
                LOG.exception(
                    "Cannot update action execution for liveaction "
                    "(id: %s, status: %s, result: %s)."
                    % (liveaction_id, status, result)
                )
                raise e

        # execution_written_to_db = date_utils.get_datetime_utc_now()

        # Those two operations are fast since they operate on two field in atomic fashion
        # with very small data
        # NOTE: Right now this is commented out since with the new DB performance optimizations we
        # don't really need this anymore (actual DB save times now rarely take more than couple of
        # fields on live action, but that would only save us ~300ms at most for large executions..
        # This way we save two queries and up to 500ms for very large executions.
        """
        operations = {
            "set__end_timestamp": live_action_written_to_db_dt,
            "set__result_size": result_size,
        }
        LiveAction.update(liveaction_db, publish=False, **operations)

        operations = {
            "set__end_timestamp": execution_written_to_db,
            "set__result_size": result_size,
        }
        ActionExecution.update(execution_db, publish=False, **operations)
        """

        return liveaction_db

    def _get_entry_point_abs_path(self, pack, entry_point):
        return content_utils.get_entry_point_abs_path(
            pack=pack, entry_point=entry_point
        )

    def _get_action_libs_abs_path(self, pack, entry_point):
        return content_utils.get_action_libs_abs_path(
            pack=pack, entry_point=entry_point
        )

    def _get_rerun_reference(self, context):
        execution_id = context.get("re-run", {}).get("ref")
        return ActionExecution.get_by_id(execution_id) if execution_id else None

    def _get_runner(self, runner_type_db, action_db, liveaction_db):
        resolved_entry_point = self._get_entry_point_abs_path(
            action_db.pack, action_db.entry_point
        )
        context = getattr(liveaction_db, "context", dict())
        user = context.get("user", cfg.CONF.system_user.user)
        config = None

        # Note: Right now configs are only supported by the Python runner actions
        if (
            runner_type_db.name == "python-script"
            or runner_type_db.runner_module == "python_runner"
        ):
            LOG.debug("Loading config from pack for python runner.")
            config_loader = ContentPackConfigLoader(pack_name=action_db.pack, user=user)
            config = config_loader.get_config()

        runner = get_runner(name=runner_type_db.name, config=config)

        # TODO: Pass those arguments to the constructor instead of late
        # assignment, late assignment is awful
        runner.runner_type = runner_type_db
        runner.action = action_db
        runner.action_name = action_db.name
        runner.liveaction = liveaction_db
        runner.liveaction_id = str(liveaction_db.id)
        runner.execution = ActionExecution.get(liveaction__id=runner.liveaction_id)
        runner.execution_id = str(runner.execution.id)
        runner.entry_point = resolved_entry_point
        runner.context = context
        runner.callback = getattr(liveaction_db, "callback", dict())
        runner.libs_dir_path = self._get_action_libs_abs_path(
            action_db.pack, action_db.entry_point
        )

        # For re-run, get the ActionExecutionDB in which the re-run is based on.
        rerun_ref_id = runner.context.get("re-run", {}).get("ref")
        runner.rerun_ex_ref = (
            ActionExecution.get(id=rerun_ref_id) if rerun_ref_id else None
        )

        return runner

    def _create_auth_token(self, context, action_db, liveaction_db):
        if not context:
            return None

        user = context.get("user", None)
        if not user:
            return None

        metadata = {
            "service": "actions_container",
            "action_name": action_db.name,
            "live_action_id": str(liveaction_db.id),
        }

        ttl = cfg.CONF.auth.service_token_ttl
        token_db = access.create_token(
            username=user, ttl=ttl, metadata=metadata, service=True
        )
        return token_db

    def _delete_auth_token(self, auth_token):
        if auth_token:
            access.delete_token(auth_token.token)


def get_runner_container():
    return RunnerContainer()
