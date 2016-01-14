Changelog
=========

in development
--------------

* Allow user to pass ``env`` parameter to ``packs.setup_virtualenv`` and ``packs.install``
  action.

  This comes handy if user wants pip to use an HTTP(s) proxy (HTTP_PROXY and HTTPS_PROXY
  environment variable) when installing pack dependencies. (new feature)
* Ability to view causation chains in Trace. This helps reduce the noise when using Trace to
  identify specific issues. (new-feature)
* Filter Trace components by model types to only view ActionExecutions, Rules or TriggerInstances.
  (new-feature)
* Include ref of the most meaningful object in each trace component. (new-feature)
* Ability to hide trigger-instance that do not yield a rule enforcement. (new-feature)
* Change the rule list columns in the CLI from ref, pack, description and enabled to ref,
  trigger.ref, action.ref and enabled. This aligns closer the UI and also brings important
  information front and center. (improvement)
* Action and Trigger filters for rule list (new-feature)
* Add missing logrotate config entry for ``st2auth`` service. #2294 [Vignesh Terafast]
* Support for object already present in the DB for ``st2-rule-tester`` (improvement)
* Add ``--register-fail-on-failure`` flag to ``st2-register-content`` script. If this flag is
  provided, the script will fail and exit with non-zero status code if registering some resource
  fails. (new feature)
* Add a missing ``get_logger`` method to the `MockSensorService``. This method now returns an
  instance of ``Mock`` class which allows user to assert that a particular message has been
  logged. [Tim Ireland, Tomaz Muraus]
* Introduce a new ``abandoned`` state that is applied to executions that we cannot guarantee as
  completed. Typically happen when an actionrunner currently running some executions quits or is
  killed via TERM.
* Add new ``st2garbagecollector`` service which periodically deletes old data from the database
  as configured in the config. By default, no old data is deleted unless explicitly configured in
  the config.
* All published variables can be available in the result of ActionChain execution under the
  ``published`` property if ``display_published`` property is specified.
* Allow user to specify TTL when creating datastore item using CLI with the ``--ttl`` option.
  (improvement)
* Fix validation error when None is passed explicitly to an optional argument on action
  execution. (bug fix)
* Deprecated ``params`` action attribute in the action chain definition in favor of the new
  ``parameters`` attribute. (improvement)
* Fix action parameters validation so that only a selected set of attributes can be overriden for
  any runner parameters. (bug fix)
* Fix type in the headers parameter for the http-request runner. (bug fix)
* Fix runaway action triggers caused by state miscalculation for mistral workflow. (bug fix)
* Throw a more friendly error message if casting parameter value fails because the value contains
  an invalid type or similar. (improvement)

1.2.0 - December 07, 2015
-------------------------

* Refactor retries in the Mistral action runner to use exponential backoff. Configuration options
  for Mistral have changed. (improvement)
* Add SSH bastion host support to the paramiko SSH runner. Utilizes same connection parameters as
  the targeted box. (new feature, improvement) #2144, #2150 [Logan Attwood]
* Update action chain runner so it performs on-success and on-error task name validation during
  pre_run time. This way common errors such as typos in the task names can be spotted early on
  since there is no need to wait for the run time.
* Change ``headers`` and ``params`` ``core.http`` action paramer type from ``string`` to
  ``object``.
* Don't allow action parameter ``type`` attribute to be an array since rest of the code doesn't
  support parameters with multiple types. (improvement)
* Fix trigger parameters validation for system triggers during rule creation - make sure we
  validate the parameters before creating a TriggerDB object. (bug fix)
* Update local runner so all the commands which are executed as a different user and result in
  using sudo set $HOME variable to the home directory of the target user. (improvement)
* Fix a bug with a user inside the context of the live action which was created using alias
  execution endpoint incorrectly being set to the system user (``stanley``) instead of the
  authenticated user which triggered the execution. (bug fix)
* Include state_info for Mistral workflow and tasks in the action execution result. (improvement)
* Introduce a new ``timeout`` action execution status which represents an action execution
  timeout. Previously, executions which timed out had status set to ``failure``. Keep in mind
  that timeout is just a special type of a failure. (new feature)
* ``--debug`` flag no longer implies profiling mode. If you want to enable profiling mode, you need
  to explicitly pass ``--profile`` flag to the binary. To reproduce the old behavior, simply pass
  both flags to the binary - ``--debug --profile``.
* Fix policy loading and registering - make sure we validate policy parameters against the
  parameters schema when loading / registering policies. (bug fix, improvement)
* Fix policy trigger for action execution cancellation. (bug fix)
* Improve error reporting for static error in ActionChain definition e.g. incorrect reference
  in default etc. (improvement)
* Fix action chain so it doesn't end up in an infinite loop if an action which is part of the chain
  is canceled. (bug fix)
* Allow jinja templating to be used in ``message`` and ``data`` field for notifications.(new feature)
* Add tools for purging executions (also, liveactions with it) and trigger instances older than
  certain UTC timestamp from the db in bulk.
* Fix json representation of trace in cli. (bug fix)
* Introducing `noop` runner and `core.noop` action. Returns consistent success in a WF regardless of
  user input. (new feature)
* Add missing indexes on trigger_instance_d_b collection. (bug fix)
* Add mock classes (``st2tests.mocks.*``) for easier unit testing of the packs. (new feature)
* Add a script (``./st2common/bin/st2-run-pack-tests``) for running pack tests. (new feature)
* Modify ActionAliasFormatParser to work with regular expressions and support more flexible parameter matching. (improvement)
* Move ChatOps pack to st2 core.
* Support for formatting of alias acknowledgement and result messages in AliasExecution. (new feature)
* Support for "representation+value" format strings in aliases. (new feature)
* Support for disabled result and acknowledgement messages in aliases. (new feature)
* Add ability to write rule enforcement (models that represent a rule evaluation that resulted
  in an action execution) to db to help debugging rules easier. Also, CLI bindings to list
  and view these models are added. (new-feature)
* Purge tool now uses delete_by_query and offloads delete to mongo and doesn't perform app side
  explicit model deletion to improve speed. (improvement)

1.1.1 - November 13, 2015
-------------------------

* Improve speed of ``st2 execution list`` command by not requesting ``result`` and
  ``trigger_instance`` attributes. The effect of this change will be especially pronounced for
  installations with a lot of large executions (large execution for this purpose is an execution
  with a large result).
* Improve speed of ``st2 execution get`` command by not requesting ``result`` and
  ``trigger_instance`` attributes.
* Now when running ``st2api`` service in debug mode (``--debug``) flag, all the JSON responses are
  pretty indented.
* When using ``st2 execution list`` and ``st2 execution get`` CLI commands, display execution
  elapsed time in seconds for all the executions which are currently in "running" state.
* Fix a race condition in sensor container where a sensor which takes <= 5 seconds to shut down
  could be respawned before it exited. (bug fix) #2187 [Kale Blankenship]
* Add missing entry for ``st2notifier`` service to the logrotate config. (bug fix)
* Allow action parameter values who's type is ``object`` to contain special characters such as
  ``.`` and ``$`` in the parameter value. (bug fix, improvement)
* Allow user to specify URL which Mistral uses to talk to StackStorm API using ``mistral.api_url``
  configuration option. If this option is not provided it defaults to the old behavior of using the
  public API url (``auth.api_url`` setting). (improvement)

1.1.0 - October 27, 2015
------------------------

* Add YAQL v1.0 support to Mistral. Earlier versions are deprecated. (improvement)
* Update CLI so ``st2 run`` / ``st2 execution run`` and ``st2 execution re-run`` commands exit with
  non-zero code if the action fails. (improvement)
* Move st2auth service authentication backends to a "repo per backend" model. Backends are now also
  dynamically discovered and registered which makes it possible to easily create and use custom
  backends. For backward compatibility reasons, ``flat_file`` backend is installed And available by
  default. (new feature, improvement)
* New st2auth authentication backend for authenticating against LDAP servers -
  https://github.com/StackStorm/st2-auth-backend-ldap. (new feature)
* Default to rule being disabled if the user doesn't explicitly specify ``enabled`` attribute when
  creating a rule via the API or inside the rule metadata file when registering local content
  (previously it defaulted to enabled).
* Fix ``timestamp_lt`` and ``timestamp_gt`` filtering in the `/executions` API endpoint. Now we
  return a correct result which is expected from a user-perspective. (bug-fix)
* Enable Mistral workflow cancellation via ``st2 execution cancel``. (improvement)
* Make sure that alias execution endpoint returns a correct status code and error message if the
  referenced action doesn't exist.
* Allow action-alias to be created and deleted from CLI.
* Allow user to select ``keystone`` backend in the st2auth service. (bug-fix)
* Fix ``packs.info`` action so it correctly exists with a non-zero status code if the pack doesn't
  exist or if it doesn't contain a valid ``.gitinfo`` file. (bug-fix)
* Fix ``packs.info`` action so it correctly searches all the packs base dirs. (bug-fix)
* Add support for ``--profile`` flag to all the services. When this flag is provided service runs
  in the profiling module which means all the MongoDB queries and query related profile data is
  logged. (new-feature)
* Introduce API Keys that do not expire like Authentication tokens. This makes it easier to work
  with webhook based integrations. (new-feature)
* Allow user to define trigger tags in sensor definition YAML files. (new feature) #2000
  [Tom Deckers]
* Fix a bug in ``stdout`` and ``stderr`` consumption in paramiko SSH runner where reading a fixed
  chunk byte array and decoding it could result in multi-byte UTF-8 character being read half way
  resulting in UTF-8 decode error. This happens only when output is greater than default chunk size
  (1024 bytes) and script produces utf-8 output. We now collect all the bytes from channel
  and only then decode the byte stream as utf-8.
* Update CLI so it supports caching tokens for different users (it creates a different file for each
  user). This means you can now use ``ST2_CONFIG_FILE`` option without disabling token cache.
  (improvement)
* Cleanup timers and webhook trigger definitions once all rules referencing them are removed. (bug-fix)
* Enable pseudo tty when running remote SSH commands with the paramiko SSH runner. This is done
  to match existing Fabric behavior. (bug-fix)
* Fix CLI so it skips automatic authentication if credentials are provided in the config on "auth"
  command. (bug fix)
* Strip the last '\r' or '\r\n' from both ``stdout`` and ``stderr`` streams from paramiko and local
  runner output. This is done to be compatible with fabric output of those streams. (bug-fix)
* Include parameters when viwewing output an execution on the CLI. (improvement)
* CLI renders parameters and output as yaml for better readability. (improvement)
* Set env variables (user provided and system assigned) before running remote command or script
  action with paramiko. (bug-fix)
* Fix a bug in Paramiko SSH runner where ``cwd`` could just be accessed in sudo mode but ``cd``
  was outside scope of ``sudo`` in the command generated. Now, ``cd`` is inside the scope of
  ``sudo``. (bug-fix)
* Fix a bug in Paramiko SSH runner where kwargs keys in script arguments were not shell
  injection safe. For example, kwarg key could contain spaces. (bug-fix)
* Fix a bug in Paramiko SSH runner where JSON output in ``stdout`` or ``stderr`` wasn't transformed
  to object automatically. (bug-fix)
* Paramiko SSH runner no longer runs a remote command with ``sudo`` if local user and remote user
  differ. (bug-fix)
* Fix a bug with the CLI token precedence - now the auth token specified as an environment variable
  or as a command line argument has precedence over credentials in the CLI config. (bug fix)
* Support versioned APIs for auth controller. For backward compatibility, unversioned API calls
  get redirected to versioned controllers by the server. (improvement)
* Add option to verify SSL cert for HTTPS request to the core.http action. (new feature)
* Update remote runner to include stdout and stderr which was consumed so far when a timeout
  occurs. (improvement)
* Fix st2-self-check script to check whether to use http/https when connecting to st2, to disable
  Windows test by default, and to check test status correctly. (bug-fix)
* Reduce the wait time between message consumption by TriggerWatcher to avoid latency (improvement)
* Use exclusive messaging Qs for TriggerWatcher to avoid having to deal with old messages
  and related migration scripts. (bug-fix)
* Allow user to specify value for the ``From`` field in the ``sendmail`` action by passing ``from``
  parameter to the action. (improvement)
  [pixelrebel]
* Allow user to update / reinstall Python dependencies listed in ``requirements.txt`` inside the
  pack virtual environment by passing ``update=True`` parameter to ``packs.setup_virtualenv``
  action or by using new ``packs.update_virtualenv`` action. (new feature)
  [jsjeannotte]
* Pack on install are now assigned an owner group. The ``pack_group`` property allows to pick this
  value and default is ``st2packs``. (new feature)
* Make sure sensor container child processes (sensor instance processes) are killed and cleaned up
  if the sensor container is forcefully terminated (SIGKILL). (bug fix, improvement)

0.13.2 - September 09, 2015
---------------------------

* Private_key supplied for remote_actions is now used to auth correctly. private_key argument
  should be the contents of private key file (of user specified in username argument). (bug-fix)
* Last newline character ('\n') is now stripped from ``stdout`` and ``stderr`` fields in local
  and remote command/shell runners. (improvement)
* Fix sensor container service so the ``config`` argument is correctly passed to the sensor
  instances in the system packs. Previously, this argument didn't get passed correctly to the
  FileWatchSensor from the system linux pack. (bug-fix)
* Make sure sensor processes correctly pick up parent ``--debug`` flag. This makes debugging a lot
  easier since user simply needs to start sensor container with ``--debug`` flag and all the sensor
  logs with level debug or higher will be routed to the container log. (improvement)

0.13.2 - September 09, 2015
---------------------------

* ``private_key`` supplied for remote_actions is now used to auth correctly.
  ``private_key`` argument should be the contents of private key file (of user specified in username argument). (bug-fix)
* Last newline character ('\n') is now stripped from ``stdout`` and ``stderr`` fields in
  local and remote command/shell runners. (improvement)
* Fix sensor container service so the ``config`` argument is correctly passed to the sensor
  instances in the system packs. Previously, this argument didn't get passed correctly to
  the FileWatchSensor from the system linux pack. (bug-fix)
* Make sure sensor processes correctly pick up parent ``--debug`` flag. This makes
  debugging a lot easier since user simply needs to start sensor container with ``--debug``
  flag and all the sensor logs with level debug or higher will be routed to the container
  log. (improvement)

0.13.1 - August 28, 2015
------------------------

* cwd for paramiko script runner should use cwd provided as runner parameter. (bug-fix)
* Fix timer regression; bring brake broken timers. (bug-fix)
* Updates to trace objects are done via non-upsert updates by adding to the array. This
  makes it safer to update trace objects from multiple processes. (bug-fix)

0.13.0 - August 24, 2015
------------------------

* Add new OpenStack Keystone authentication backend.
  [Itxaka Serrano]
* Information about parent workflow is now a dict in child's context field. (improvement)
* Fix a bug when some runner parameter default values where not overridden when a
  falsey value was used in the action metadata parameter override (e.g. False, 0).
  [Eugen C.]
* Correctly return 404 if user requests an invalid path which partially maps to an existing
  path. (bug-fix)
* Add support for restarting sensors which exit with a non-zero status code to
  the sensor container. Sensor container will now automatically try to restart
  (up to 2 times) sensor processes which die with a non-zero status code. (improvement)
* Support for RabbitMQ cluster. StackStorm works with a RabbitMQ cluster and switches
  nodes on failover. (feature)
* Add index to the ActionExecution model to speed up query. (improvement)
* Fix sort key in the ActionExecution API controller. (bug-fix)
* Introduce a Paramiko SSH runner that uses eventlets to run scripts or commands in parallel. (improvement) (experimental)
* Add action parameters validation to Mistral workflow on invocation. (improvement)
* Fix key name for error message in liveaction result. (bug-fix)
* Fix 500 API response when rule with no pack info is supplied. (bug-fix)
* Fix bug in trigger-instance re-emit (extra kwargs passed to manager is now handled). (bug-fix)
* Rename notification "channels" to "routes". (improvement)
* Make sure auth hook and middleware returns JSON and "Content-Type: application/json" header
  in every response. (improvement, bug-fix)
* Fix bug in triggers emitted on key value pair changes and sensor spawn/exit. When
  dispatching those triggers, the reference used didn't contain the pack names
  which meant it was invalid and lookups in the rules engine would fail. (bug-fix)
* Allow user to include files which are written on disk inside the action create API payload.
  (new feature)
* Allow user to retrieve content of a file inside a pack by using the new
  ``/packs/views/files/`` API endpoint. (new feature)
* Handle sudo in paramiko remote script runner. (bug-fix)
* Turn on paramiko ssh runner as the default ssh runner in prod configuration.
  To switch to fabric runner, set ``use_paramiko_ssh_runner`` to false in st2.conf. (improvement)
* Add OpenStack Keystone authentication configuration for Mistral. (improvement)
* Abiltiy to add trace tag to TriggerInstance from Sensor. (feature)
* Ability to view trace in CLI with list and get commands. (feature)
* Add ability to add trace tag to ``st2 run`` CLI command. (feature)
* Add ability to specify trace id in ``st2 run`` CLI command. (feature)
* Update ``st2ctl`` to correctly start ``st2web`` even if even if Mistral is no installed.
  (bug-fix, improvement)
* Add X-Request-ID header to all API calls for easier debugging. (improvement)
* Add new CLI commands for disabling and enabling content pack resources
  (``{sensor,action,rule} {enable, disable} <ref or id>``) (feature)
* Fix a bug in handling positional arguments with spaces. (bug-fix)
* Make sure that the ``$PATH`` environment variable which is set for the sandboxed Python
  process contains "<virtualenv path>/bin" directory as the first entry. (bug fix)

0.12.2 - August 11, 2015
------------------------

* Support local ssh config file in remote runners. (feature)
* Changes to htpasswd file used in `flat_file` auth backend do not require
  a restart of st2auth and consequently StackStorm. (feature)

0.12.1 - July 31, 2015
----------------------

* Un-registering a pack also removes ``rules`` and ``action aliases`` from the pack. (bug-fix)
* Disable parallel SSH in fabric runner which causes issues with eventlets. (bug-fix)
* Fix executions stuck in ``running`` state if runner container throws exception. (bug-fix)
* Fix cases where liveaction result in dict are escaped and passed to Mistral. (bug-fix)

0.12.0 - July 20, 2015
----------------------

* Add support for script arguments to the Windows script runner. (new feature)
  [James Sigurðarson]
* Allow user to filter executions on trigger instance id.
  [Sayli Karmarkar]
* By default the following environment variables are now available to the actions executed by
  local, remote and python runner: ``ST2_ACTION_API_URL``, ``ST2_ACTION_AUTH_TOKEN``. (new-feature)
* Jinja filter to make working with regex and semver possible in any place that
  support jinja (improvement)
* New experimental workflow runner based on the open-source CloudSlang project. (new-feature)
  [Eliya Sadan, Meir Wahnon, Sam Markowitz]
* Update all the code to handle all the ``datetime`` objects internally in UTC. (improvement,
  bug-fix)
* Allow users to use ``timediff_lt`` and ``timediff_gt`` rule comparison operator with many string
  date formats - previously it only worked with ISO8601 date strings. (improvement)
* Allow user to specify new ``secret`` attribute (boolean) for each action parameters. Values of
  parameters which have this attribute set to true will be masked in the log files. (new-feature)
* API server now gracefully shuts down on SIGINT (CTRL-C). (improvement)
* Fix a bug with with reinstalling a pack with no existing config - only try to move the config
  file over if it exists. (bug fix)
* Support for masking secret parameters in the API responses. Secret parameters can only be viewed
  through the API by admin users. (new-feature)
* Single sensor mode of Sensor Container uses ``--sensor-ref`` instead of ``--sensor-name``.
* ``six`` library is now available by default in the Python sandbox to all the newly installed
  packs. (improvement)
* Dispatch an internal trigger when a datastore item has been created, updated, deleted and when
  it's value has changed. (new-feature)
* Fix a bug with ``st2 execution list`` CLI command throwing an exception on failed Mistral
  workflows. (bug-fix)
* Fix a bug with ``st2 execution list`` CLI command not displaying ``end_timestamp`` attribute for
  Mistral workflows. (bug-fix)
* Add new ``/v1/packs`` API endpoint for listing installed packs. (new-feature)
* Ability to partition sensors across sensor nodes using various partition schemes. (new-feature)
* Add ability to use action context params as action params in meta. (new-feature)
* Fix a bug in action container where rendering params was done twice. (bug-fix)
* Move /exp/actionalias/ and /exp/aliasexecution to /v1/actionalias/ and /v1/aliasexecution/
  respectively. (upgrade)
* Display friendly message for error in parameters validation on action execution. (improvement)

0.11.6 - July 2, 2015
---------------------

* Update all the code to handle all the datetime objects internally in UTC. (improvement, bug-fix)

0.11.5 - July 1, 2015
---------------------

* Fix a bug where ``end_timestamp`` is not captured for Mistral workflow executions (bug-fix)
* Fix a bug where the CLI failed to display Mistral workflow that errored (bug-fix)
* Fix a bug where the published variables is not captured in the Mistral workflow result (bug-fix)

0.11.4 - June 30, 2015
----------------------

* Remove unnecessary rule notify_hubot from core.

0.11.3 - June 16, 2015
----------------------

* Fix RHEL6 packaging issues

0.11.2 - June 12, 2015
----------------------

* Fix a bug with ``start_timestamp`` and ``end_timestamp`` sometimes returning an invalid value in
  a local instead of UTC timezone. (bug-fix)
* Fix to get PollingSensor working again. Sensors of type PollingSensor were not being treated
  as such and as a result would fail after the 1st poll. (bug-fix)

0.11.1 - June 8, 2015
---------------------

* Action aliases are registered by default. (improvement)
* Repair failing pack installation. (bug-fix)

0.11.0 - June 5, 2015
---------------------

* Allow user to configure the CLI using an ini style config file located at ``~/.st2rc``.
  (new-feature)
* Add support for caching of the retrieved auth tokens to the CLI. (new-feature)
* Throw a more-user friendly exception when enforcing a rule if an action referenced inside
  the rule definition doesn't exist. (improvement)
* Fix a bug with the rule evaluation failing if the trigger payload contained a key with a
  dot in the name. (bug-fix)
* Fix a bug with publishing array (list) values as strings inside the action chain workflows.
  (bug-fix)
* Update CLI so it displays the error at the top level when using ``run``, ``execution run`` or
  ``execution get`` when executed workflow fails. (improvement)
* Action trigger now contains execution id as opposed to liveaction id. (bug-fix)
* Add new API endpoint for re-running an execution (``POST /executions/<id>/re_run/``).
  (new-feature)
* Rules should be part of a pack. (improvement)
* Update Windows runner code so it also works with a newer versions of winexe (> 1.0).
  (improvement)
  [James Sigurðarson]
* CLI now has ``get`` and ``list`` commands for triggerinstance. (new-feature)
* Validate parameters during rule creation for system triggers. (improvement)
* CLI now has ``re-emit`` command for triggerinstance. (new-feature)

v0.9.2 - May 26, 2015
---------------------

* Fix broken ``packs.download`` action. (bug-fix)

v0.9.1 - May 12, 2015
---------------------

* Allow option to bypass SSL Certificate Check (improvement)
* Fix a bug with alias parser to support empty formats (bug-fix)
* Return HTTP BAD REQUEST when TTL requested for token > Max configured TTL (improvement)

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
* Change default mode for authentication to standalone. (refactor)

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
