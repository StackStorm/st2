Changelog
=========

in development
--------------

* Allow user to configure the CLI using an ini style config file located at ``~/.st2rc``.
  (new-feature)
* Add support for caching of the retrieved auth tokens to the CLI. (new-feature)
* Throw a more-user friendly exception when enforcing a rule if an action referenced inside
  the rule definition doesn't exist. (improvement)
* Fix a bug with the rule evaluation failing if the trigger payload contained a key with a
  dot in the name. (bug-fix)

v0.9.0 - April 29, 2015
-----------------------

* Report a more user-friendly error if an action-chain task references an invalid or inexistent
  action. Also treat invalid / inexistent action as a top-level action-chain error. (improvement)
* Report a more user-friendly error if an action-chain definition contains an invalid type.
  (improvement)
* Enable authentication by default for package based installations.
* Rename all st2 processes to be prefixed by st2. (sensor_container is now st2sensorcontainer,
  rules_engine is now st2rulesengine, actionrunner is now st2actionrunner) (improvement)
* Return a user friendly error on no sensors found or typo in sensor class name in single
  sensor mode. (improvement)
* Sensor container now returns non-zero exit codes for errors. (bug-fix)
* Check if internal trigger types are already registered before registering
  them again. (improvement)
* Sensor container now can dynamically load/reload/unload sensors on data model changes.
  (new-feature)
* Fix a bug in datastore operations exposed in st2client. (bug-fix)
* Catch exception if rule operator functions throw excepton and ignore the rule. (bug-fix)
* Remove expected "runnertype not found" error logs on action registration
  in clean db. (improvement)
* Clean up rule registrar logging. (improvement)
* Add ``-t`` / ``--only-token`` flag to the ``st2 auth`` command. (new-feature)
* ``register`` param in packs.install should be passed to packs.load. (bug-fix)
* Fix validation code to validate value types correctly. (bug-fix)
* Add ability to best-effort cancel actions and actionchain via API. (new-feature)
* Add new ``windows-cmd`` and ``windows-script`` runners for executing commands
  and PowerShell scripts on Windows hosts. (new-feature)
* Update runner names so they follow a consistent naming pattern. For backward
  compatibility reasons, runners can still be referenced using their old names.
  (improvement)
* Update all the Python services to re-open log files on the ``SIGUSR1`` signal. (new-feature)
* Internal trigger types registered using APIs should use auth token. (bug-fix)

v0.8.3 - March 23, 2015
-----------------------

* Don't allow ``run-remote-script`` actions without an ``entry_point`` attribute - throw an
  exception when running an action. (improvement)
* Fix ``packs.setup_virtualenv`` command so it works correctly if user specified multiple packs
  search paths. (bug-fix)
* Update sensor container to use ``auth.api_url`` setting when talking to the API (e.g. when
  accessing a datastore, etc.). This way it also works correctly if sensor container is running
  on a different host than the API. (bug-fix)

v0.8.2 - March 10, 2015
-----------------------

* Fix a bug with python-runner actions sometimes not correctly reporting the action's ``stdout``.
  (bug-fix)
* Fix a bug in the ``run-remote-script`` runner - the runner ignored environment variables and
  authentication settings which were supplied to the action as parameters. (bug-fix)

v0.8.1 - March 10, 2015
-----------------------

Docs: http://docs.stackstorm.com/0.8/

* Allow user to exclude particular attributes from a response by passing
  ``?exclude_attributes=result,trigger_instance`` query parameter to the ``/actionexecutions/``
  and ``/actionexecutions/<execution id>/`` endpoint (new-feature)
* Add new ``/actionexecutions/<id>/attribute/<attribute name>`` endpoint which allows user to
  retrieve a value of a particular action execution attribute. (new-feature)
* Update ``execution get`` CLI command so it automatically detects workflows and returns more
  user-friendly output by default. (improvement)
* Update ``run``, ``action execute``, ``execution get`` and ``execution re-run`` CLI commands to
  take the same options and return output in the same consistent format.
* Fix a bug with http runner not parsing JSON HTTP response body if the content-type header also
  contained a charset. (bug-fix)
* Indent workflow children properly in CLI (bug-fix)
* Make sure that wait indicator is visible in CLI on some systems where stdout is buffered. (bug-fix)
* Fix a bug with ``end_timestamp`` attribute on the ``LiveAction`` and ``ActionExecution`` model
  containing an invalid value if the action hasn't finished yet. (bug-fix)
* Correctly report an invalid authentication information error in the remote runner. (bug-fix)
* Throw a more friendly error in the action chain runner if it fails to parse the action chain
  definition file. (improvement)
* Fix a bug in the action chain runner and make sure action parameters are also available for
  substitution in the ``publish`` scope. (bug-fix)

v0.8.0 - March 2, 2015
----------------------

Docs: http://docs.stackstorm.com/0.8/

* Allow user to specify current working directory (``cwd`` parameter) when running actions using the
  local or the remote runner (``run-local``, ``run-local-script``, ``run-remote``,
  ``run-remote-script``). (new-feature)
* Default values of the parameter of an Action can be system values stored in kv-store. (new-feature)
* Allow users to specify additional paths where StackStorm looks for integration packs using
  ``packs_base_paths`` setting. (new-feature)
* Allow user to specify which Python binary to use for the Python runner actions using
  ``actionrunner.python_binary`` setting (new-feature)
* Default Python binary which is used by Python runner actions to be the Python binary which is
  used by the action runner service. Previous, system's default Python binary was used.
* Fix a race-condition / bug which would occur when multiple packs are installed at the same time.
  (bug-fix)
* Vars can be defined in the ActionChain. (new-feature)
* Node in an ActionChain can publish global variables. (new-feature)
* Allow user to provide authentication token either inside headers (``X-Auth-Token``) or via
  ``x-auth-token`` query string parameter. (new-feature)
* Allow actions without parameters. (bug-fix)
* Fix a bug with rule matching not working for any triggers with parameters. (bug-fix)
* Require ``cmd`` parameter for the following actions: ``core.remote``, ``core.remote_sudo``,
  ``core.local``, ``core.local_sudo`` (bug-fix)
* Allow user to override authentication information (username, password, private key) on per
  action basis for all the remote runner actions. (new-feature)
* Allow user to pass ``--inherit-env`` flag to the ``st2 action run`` command which causes all
  the environment variables accessible to the CLI to be sent as ``env`` parameter to the action
  being executed. (new-feature)
* Cast params of an execution before scheduling in the RulesEngine. This allows non-string
  parameters in an action. (new-feature)
* Use QuerySet.count() instead of len(QuerySet) to avoid the caching of the entire result which
  improve running time of API request. (bug-fix)
* CLI commands to return non-zero exit codes for failed operations (new-feature)
* Fix a bug with template rendering, under some conditions, ending in an infinite loop. (bug-fix)
* Rename ActionExecution to LiveAction. (refactor)
* Rename ActionExecutionHistory to ActionExecution. (refactor)
* A separate history process is no longer required. ActionExecution updates are carried at time of
  update to LiveAction. (refactor)
* Add new ``nequals`` (``neq``) rule criteria operator. This criteria operator
  performs not equals check on values of an arbitrary type. (new-feature)
* Mistral subworkflows kicked off in st2 should include task name. (bug-fix)
* Add new ``execution re-run <execution id>`` CLI command for re-running an
  existing action. (new-feature)
* Dispatch an internal trigger when a sensor process is spawned / started
  (``st2.sensor.process_spawn``) and when a process exits / is stopped
  (``st2.sensor.process_exit``). (new-feature)
* Update HTTP runner to automatically parse JSON response body if Content-Type is
  ``application/json`` (new-feature)
* API url /v1/actionexecutions/ is now deprecated in favor of /v1/executions/ (refactor)
* API url change /v1/history/execution to /v1/executions (refactor)
* API url change /v1/history/execution/views/filters to /v1/executions/views/filters (refactor)
* POST to /v1/executions take LiveActionAPI but returns ActionExecutionAPI (refactor)
* Support for filtering by timestamp and status in executions list. (new-feature)
* Execution list shows only top level executions by default to see full list use --showall. (refactor)
* Ability to see child tasks of any execution. (new-feature)
* Allow sensors to manage global datastore items via sensor_service by passing ``local=False``
  argument to the ``get_value``, ``set_value`` and ``delete_value`` methods. (new-feature)
* Allow sensors to list datastore items using ``list_values`` sensor_service method. (new-feature)
* Allow users to filter datastore items by name prefix by passing ``?prefix=<value>`` query
  parameter to the /keys endpoint. (new-feature)
* Fix non-string types to be rendered correctly in action parameters when used in rule. (bug-fix)
* Allow user to specify default value for required attributes in the definition of action
  parameters. (bug-fix)
* When running with auth enabled, correctly preserve the username of the authenticated user who
  has triggered the action execution. (bug-fix)

v0.7 - January 16, 2015
-----------------------

Docs: http://docks.stackstorm.com/0.7/

* Python runner and all the fabric based runners (``run-local``, ``run-local-script``,
  ``run-remote``, ``run-remote-script``) now expose ``timeout`` argument. With this argument
  user can specify action timeout. Previously, the action timeout was not user-configurable and
  a system-wide default value was used.
* The time when an action execution has finished is now recorded and available via the
  ``end_timestamp`` attribute on the ``ActionExecution`` model.
* Status code 400 (bad request) is now returned if user doesn't provide a body to API endpoints
  which require it. Previously 500 internal server error was returned (bug-fix).
* Refactor local runners so they are more robust, efficient and easier to debug. Previously, local
  actions were executed through SSH, now they are executed directly without the overhead of SSH.
* Fix local runner so it correctly executes a command under the provider system user if ``user``
  parameter is provided. (bug-fix)
* Fix a bug with a Trigger database object in some cases being created twice when registering a
  rule. (bug-fix)
* Fix a bug with child processes which run sensor code not being killed when stopping a sensor
  container service. (bug-fix)
* Fix a bug and allow user to use non-ascii (unicode) values in the parameter substitution values.
  (bug-fix)
* Allow polling sensors to retrieve current poll interval and change it using ``get_poll_interval``
  and ``set_poll_interval`` methods respectively. (new-feature)
* Add support for a ``standalone`` mode to the st2auth service. In the standalone mode,
  authentication is handled inside the st2auth service using the defined backend. (new feature)
* Timer is not a sensor anymore. It is spun as part of rules_engine process (refactor)
* Fix a bug with action registration where action with invalid schema for
  parameters get registered. (bug-fix)
* Fix a bug with 'default' param values inheritance in runner/actions. (bug-fix)
* Add new rule criteria comparison operators: ``iequals``, ``contains``, ``icontains``,
  ``ncontains``, ``incontains``, ``startswith``, ``istartswith``, ``endswith``, ``iendswith``
  (new-feature)
* Allow sensors to store temporary data in the datastore using the ``get_value``, ``set_value`` and
  ``delete_value`` methods exposed by sensor_service. (new-feature)
* Allow user to specify TTL for datastore values by sending ``ttl`` attribute in the body of a
  `PUT /keys/<key id>` request. (new feature)
* Add new `key delete_by_prefix --prefix=<prefix>` client command. This command allows deletion of
  all the keys which name starts with the provided prefix. (new-feature)
* Add ability to attach tags to Action, Rule and TriggerType.
* Add ability to query results asynchronously from external services. (new-feature)
* Action models now use ContentPackResourceMixin so we can get them by ref. (refactor)
* Add ``rule_tester`` tool which allows users to test rules in an offline mode without any services
  running (new-feature)
* Fix a bug where trigger objects weren't created for triggers with different parameters. (bug-fix)
* st2api only requires st2common and dependencies defined in requirements to be available on the
  pythonpath thus making it possible to run st2api standalone.
* Add support for 'exists' and 'nexists' operators in rule criteria. (new-feature)

v0.6.0 - December 8, 2014
-------------------------

Docs: http://docs.stackstorm.com/0.6.0/

* Separate virtualenv per pack. (Pythonic sensors and actions use them by default.)
* Install pip requirements from requiremets.txt in packs by default.
* Sensors are now run in their own process for isolation.
* Python Actions are now run in their own process for isolation.
* Add Sensor and PollingSensor base classes. (Sensors API change is non-backward compatible.)
* Separate out rules_engine into own process.
* YAML support for action, rules and chain meta.
* Add sensor meta support (JSON/YAML) to specify trigger types.
* Packs default path moves from /opt/stackstorm to /opt/stackstorm/packs/.
* Webhooks are not part of a sensor. They are now part of core API. (Authentication may
  be required.)
* API URLs are now versioned. All the existing paths have been prefixed with ``/v1``
  (e.g. ``/v1/actions``).
* Audit log messages are now saved in a structured format as JSON in
  ``st2actionrunner.{pid}.audit.log`` log file.
* Numerous bug fixes.

v0.5.1 - November 3rd, 2014
---------------------------

Docs: http://docs.stackstorm.com/0.5.1/

* Initial public release
