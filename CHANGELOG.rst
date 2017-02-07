Changelog
=========

in development
--------------
* Fix ``/v1/packs/views/files/<pack ref or id>`` and
  ``/v2/packs/views/files/<pack ref or id>/<file path>`` API endpoint so it
  works correctly for packs where pack name is not equal to the pack ref. (bug fix)

  Reported by skjbulcher #3128
* Improve binary file detection and fix "pack files" API controller so it works correctly for
  new-style packs which are also git repositories. (bug fix)
* Fix returning a tuple from the Python runner so it also works correctly, even if action returns
  a complex type (e.g. Python class instance) as a result. (bug fix)

  Reported by skjbulcher #3133
* Introduce validation of trigger parameters when creating a rule for non-system (user-defined)
  trigger types.

  Validation is only performed if ``system.validate_trigger_parameters`` config option is enabled
  (it's disabled by default) and if trigger object defines ``parameters_schema`` attribute.

  Contribution by Hiroyasu OHYAMA. #3094
* Introduce validation of trigger payload for non-system and user-defined triggers which is
  performed when dispatching a trigger inside a sensor and when sending a trigger via custom
  webhook.

  Validation is only performed if ``system.validate_trigger_payload`` config option is enabled
  (it's disabled by default) and if trigger object defines ``payload_schema`` attribute.

  Contribution by Hiroyasu OHYAMA. #3094
* Add support for complex rendering inside of array and object types. This allows the user to
  nest Jinja variables in array and object types.
* Fix cancellation specified in concurrency policies to cancel actions appropriately. Previously,
  mistral workflow is orphaned and left in a running state. (bug fix)
* If a retry policy is defined, action executions under the context of a workflow will not be
  retried on timeout or failure. Previously, action execution will be retried but workflow is
  terminated. (bug fix)
* Update Python runner to throw a more user-friendly exception in case action metadata file
  references a script file which doesn't exist or which contains invalid syntax. (improvement)
* Update ``st2auth`` service so it includes more context and throws a more user-friendly exception
  when retrieving an auth backend instance fails. This makes it easier to debug and spot various
  auth backend issues related to typos, misconfiguration and similar. (improvement)
* Fix how mistral client and resource managers are being used in the mistral runner. Authentication
  has changed in the mistral client. Fix unit test accordingly. (bug fix)
* Fixed issue where passing a single integer member for an array parameter for an action would
  cause a type mismatch in the API (bug fix)
* Use the newly introduced CANCELLED state in mistral for workflow cancellation. Currently, st2
  put the workflow in a PAUSED state in mistral. (improvement)
* Add support for evaluating jinja expressions in mistral workflow definition where yaql
  expressions are typically accepted. (improvement)
* Let querier plugin decide whether to delete state object on error. Mistral querier will
  delete state object on workflow completion or when the workflow or task references no
  longer exists. (improvement)

2.1.1 - December 16, 2016
-------------------------

* After running ``st2 pack install`` CLI command display which packs have been installed.
  (improvement)
* Update ``/v1/packs/register`` API endpoint so it throws on failure (e.g. invalid pack or resource
  metadata). This way the default behavior is consistent with default
  ``st2ctl reload --register-all`` behavior.

  If user doesn't want the API endpoint to fail on failure, they can pass
  ``"fail_on_failure": false`` attribute in the request payload. (improvement)
* Throw a more user-friendly exception when registering packs (``st2ctl reload``) if pack ref /
  name is invalid. (improvement)
* ``core.http`` action now also supports HTTP basic auth and digest authentication by passing
  ``username`` and ``password`` parameter to the action. (new feature)
* Fix ``GET /v1/packs/<pack ref or id>`` API endpoint - make sure pack object is correctly returned
  when pack ref doesn't match pack name. Previously, 404 not found was thrown. (bug fix)
* Update local action runner so it supports and works with non-ascii (unicode) parameter keys and
  values. (bug fix)

  Contribution by Hiroyasu OHYAMA. #3116
* Update ``packs.load`` action to also register triggers by default. (improvement)
* Update ``/v1/packs/register`` API endpoint so it registers resources in the correct order which
  is the same as order used in ``st2-register-content`` script. (bug fix)

2.1.0 - December 05, 2016
-------------------------

* Pack management changes:

  - Add new ``stackstorm_version`` and ``system`` fields to the pack.yaml metadata file. Value of the
    first field can contain a specific StackStorm version with which the pack is designed to work
    with (e.g. ``>=1.6.0,<2.2.0`` or ``>2.0.0``). This field is checked when installing / registering
    a pack and installation is aborted if pack doesn't support the currently running StackStorm version.
    Second field can contain an object with optional system / OS level dependencies.
    (new feature)
  - Add new ``contributors`` field to the pack metadata file. This field can contain a list of
    people who have contributed to the pack. The format is ``Name <email>``, e.g.
    ``Tomaz Muraus <tomaz@stackstorm.com>`` (new feature)
  - Add support for default values and dynamic config values for nested config objects. (new feature, improvement)
  - Add new ``st2-validate-pack-config`` tool for validating config file against a particular config
    schema file. (new-feature)
  - Improved pack validation - now when the packs are registered we check that:

    + ``version`` attribute in the pack metadata file matches valid semver format (e.g
      ``0.1.0``, ``2.0.0``, etc.)
    + ``email`` attribute (if specified) contains a valid email address. (improvement)
    + Only valid word characters (``a-z``, ``0-9`` and ``_``) used for action parameter
      names. Previously, due to bug in the code, any character was allowed.

    If validation fails, pack registration will fail. If you have an existing action or pack definition which
    uses invalid characters, pack registration will fail. **You must update your packs**.
  - For consistency with new pack name validation changes, sample ``hello-st2`` pack has been renamed
    to ``hello_st2``.
  - Fix ``packs.uninstall`` action so it also deletes ``configs`` and ``policies`` which belong to
    the pack which is being uninstalled. (bug fix)
  - Update ``packs.install`` action (``pack install`` command) to only load resources from the packs
    which are being installed. Also update it and remove "restart sensor container" step from the
    install workflow. This step hasn't been needed for a while now because sensor container
    dynamically reads a list of available sensors from the database and starts the sub processes.
    (improvement)
  - Remove ``packs.info`` action because ``.gitinfo`` file has been deprecated with the new pack
    management approach. Now pack directories are actual checkouts of the corresponding pack git
    repositories so this file is not needed anymore.

* Add new ``POST /v1/actionalias/match`` API endpoint which allows users to perform ChatOps action
  alias matching server-side. This makes it easier to build and maintain StackStorm ChatOps
  clients / adapters for various protocols and mediums. Clients can now be very thin wrappers
  around this new API endpoint.

  Also add two new corresponding CLI commands - ``st2 alias-execution match`` and
  ``st2 alias-execution execute``. Contribution by Anthony Shaw. (new feature) #2895.
* Adding ability to pass complex array types via CLI by first trying to
  seralize the array as JSON and then falling back to comma separated array.
* Add new ``core.pause`` action. This action behaves like sleep and can be used inside the action
  chain or Mistral workflows where waiting / sleeping is desired before proceeding with a next
  task. Contribution by Paul Mulvihill. (new feature) #2933. 
* When a policy cancels a request due to concurrency, it leaves end_timestamp set to None which
  the notifier expects to be a date. This causes an exception in "isotime.format()". A patch was
  released that catches this exception, and populates payload['end_timestamp'] with the equivalent
  of "datetime.now()" when the exception occurs.
* Adding check for datastore Client expired tokens used in sensor container
* Improve API exception handling and make sure 400 status code is returned instead of 500 on
  mongoengine field validation error. (improvement)
* Throw a more user-friendly exception if rendering a dynamic configuration value inside the config
  fails. (improvement)
* Change st2api so that a full execution object is returned instead of an error message, when an
  API client requests cancellation of an execution that is already canceled
* Speed up short-lived Python runner actions by up to 70%. This way done by re-organizing and
  re-factoring code to avoid expensive imports such as jsonschema, jinja2, kombu and mongoengine
  in the places where those imports are not actually needed and by various other optimizations.
  (improvement)
* Improve performance of ``GET /executions/views/filters`` by creating additional indexes on
  executions collection
* Allow user to supply multiple resource ids using ``?id`` query parameter when filtering
  "get all" API endpoint result set (e.g. `?id=1,2,3,4`). This allows for a better client and
  servers performance when user is polling and interested in multiple resources such as polling on
  multiple action executions. (improvement)
* Upgrade various internal Python library dependencies to the latest stable versions (gunicorn,
  kombu, six, appscheduler, passlib, python-gnupg, semver, paramiko, python-keyczar, virtualenv).
* Add support for ssh config file for ParamikoSSHrunner. Now ``ssh_config_file_path`` can be set
  in st2 config and can be used to access remote hosts when ``use_ssh_config`` is set to
  ``True``. However, to access remote hosts, action paramters like username and
  password/private_key, if provided with action, will have precedence over the config file
  entry for the host. #2941 #3032 #3058 [Eric Edgar] (improvement)
* Fix python action runner actions and make sure that modules from ``st2common/st2common/runners``
  directory don't pollute ``PYTHONPATH`` for python runner actions. (bug fix)

2.0.1 - September 30, 2016
--------------------------

* Fix ``st2 execution get`` command so now ``--attr`` argument correctly works with child
  properties of the ``result`` and ``trigger_instance`` dictionary (e.g. ``--attr
  result.stdout result.stderr``). (bug fix)
* Update traces list API endpoint and ``st2 trace list`` so the traces are sorted by
  ``start_timestamp`` in descending order by default. This way it's consistent with executions
  list and ``-n`` CLI parameter works as expected. (improvement)
* Allow users to specify sort order when listing traces using the API endpoint by specifying
  ``?sort_desc=True|False`` query parameters and by passing ``--sort=asc|desc`` parameter to
  the ``st2 trace list`` CLI command. (improvement)
* Fix a bug with action default parameter values not supporting Jinja template
  notation for parameters of type ``object``. (bug fix, improvement)
* Fix ``--user`` / ``-u`` argument in the ``st2 key delete`` CLI command.
* Retry connecting to RabbitMQ on services start-up if connecting fails because
  of an intermediate network error or similar. (improvements)
* Allow jinja expressions ``{{st2kv.system.foo}}`` and ``{{st2kv.user.foo}}`` to access
  datastore items from workflows, actions and rules. This is in addition to supporting
  expressions ``{{system.foo}}`` and ``{{user.foo}}``. In subsequent releases, the expressions
  ``{{system.}}`` and ``{{user.}}`` will be deprecated. It is recommended to switch to using
  ``{{st2kv.system.}}`` and ``{{st2kv.user.}}`` for your content. (improvement)

2.0.0 - August 31, 2016
-----------------------

* Implement custom Jinja filter functions ``to_json_string``, ``to_yaml_string``,
  ``to_human_time_from_seconds`` that can be used in actions and workflows. (improvement)
* Refactor Jinja filter functions into appropriate modules. (improvement)
* Default chatops message to include time taken to complete an execution. This uses
  ``to_human_time_from_seconds`` function. (improvement)
* Fix a bug when jinja templates with filters (for example,
  ``st2 run core.local cmd='echo {{"1.6.0" | version_bump_minor}}'``) in parameters wasn't rendered
  correctly when executing actions. (bug-fix)
* Allow user to cancel multiple executions using a single invocation of ``st2 execution cancel``
  command by passing multiple ids to the command -
  ``st2 execution cancel <id 1> <id 2> <id n>`` (improvement)
* We now execute --register-rules as part of st2ctl reload. PR raised by Vaishali:
  https://github.com/StackStorm/st2/issues/2861#issuecomment-239275641
* Bump default timeout for ``packs.load`` command from ``60`` to ``100`` seconds. (improvement)
* Change Python runner action and sensor Python module loading so the module is still loaded even if
  the module name clashes with another module which is already in ``PYTHONPATH``
  (improvement)
* Fix validation of the action parameter ``type`` attribute provided in the YAML metadata.
  Previously we allowed any string value, now only valid types (object, string, number,
  integer, array, null) are allowed. (bug fix)
* Upgrade pip and virtualenv libraries used by StackStorm pack virtual environments to the latest
  versions (8.1.2 and 15.0.3).
* Allow user to list and view rules using the API even if a rule in the database references a
  non-existent trigger. This shouldn't happen during normal usage of StackStorm, but it makes it
  easier for the user to clean up in case database ends up in a inconsistent state. (improvement)
* Update ``packs.uninstall`` command to print a warning message if any rules in the system
  reference a trigger from a pack which is being uninstalled. (improvement)
* Fix disabling and enabling of a sensor through an API and CLI. (bug-fix)
* Fix HTTP runner so it works correctly when body is provided with newer versions of requests
  library (>= 2.11.0). (bug-fix) #2880

  Contribution by Shu Sugimoto.

1.6.0 - August 8, 2016
----------------------

* Upgrade to pymongo 3.2.2 and mongoengine 0.10.6 so StackStorm now also supports and works with
  MongoDB 3.x. (improvement)
* Make sure policies which are disabled are not applied. (bug fix)
  Reported by Brian Martin.
* Allow user to specify an action which is performed on an execution (``delay``, ``cancel``) when a
  concurrency policy is used and a defined threshold is reached. For backward compatibility,
  ``delay`` is a default behavior, but now user can also specify ``cancel`` and an execution will
  be canceled instead of delayed when a threshold is reached.
* Update action runner to use two internal green thread pools - one for regular (non-workflow) and
  one for workflow actions. Both pool sizes are user-configurable. This should help increase the
  throughput of a single action runner when the system is not over-utilized. It can also help
  prevent deadlocks which may occur when using delay policies with action-chain workflows.
  (improvement)
* Update CLI commands to make sure that all of them support ``--api-key`` option. (bug-fix)
* Add support for sorting execution list results, allowing access to oldest items. (improvement)
* Allow administrator to configure maximum limit which can be specified using ``?limit``
  query parameters when making API calls to get all / list endpoints. For backward compatibility
  and safety reasons, the default value still is ``100``. (improvement)
* Update ``st2-register-content`` script to exit with non-zero on failure (e.g. invalid resource
  metadata, etc.) by default. For backward compatibility reasons, ``--register-fail-on-failure``
  flag was left there, but it now doesn't do anything since this is the default behavior. For ease
  of migrations, users can revert to the old behavior by using new
  ``--register-no-fail-on-failure`` flag. (improvement)
* Allow Python runner actions to return execution status (success, failure) by returning a tuple
  from the ``run()`` method. First item in the tuple is a flag indicating success (``True`` /
  ``False``) and the second one is the result. Previously, user could only cause action to fail by
  throwing an exception or exiting which didn't allow for a result to be returned. With this new
  approach, user can now also return an optional result with a failure. (new feature)
* Include a chatops alias sample in ``examples`` pack that shows how to use ``format`` option to
  display chatops messages in custom formatted way. (improvement)
* Fix ``Internal Server Error`` when an undefined jinja variable is used in action alias ack field.
  We now send a http status code ``201`` but also explicitly say we couldn't render the ``ack``
  field. The ``ack`` is anyways a nice-to-have message which is not critical. Previously, we still
  kicked off the execution but sent out ``Internal Server Error`` which might confuse the user
  whether execution was kicked off or not. (bug-fix)
* Include testing for chatops ``format_execution_result`` python action. The tests cover various
  action types. (improvement)
* Include a field ``elapsed_seconds`` in execution API response for GET calls. The clients using
  the API can now use ``elapsed_seconds`` without having to repeat computation. (improvement)
* Update ``st2-register-content`` script so it validates new style configs in
  ``/opt/stackstorm/configs/`` directory when using ``--register-configs`` flag if a pack contains
  a config schema (``config.schema.yaml``). (improvement)
* Implement custom YAQL function ``st2kv`` in Mistral to get key-value pair from StackStorm's
  datastore. (new-feature)

1.5.1 - July 13, 2016
---------------------

* Fix trigger registration when using st2-register-content script with ``--register-triggers``
  flag. (bug-fix)
* Fix an issue with CronTimer sometimes not firing due to TriggerInstance creation failure.
  (bug-fix)
  Reported by  Cody A. Ray
* Add support for default values when a new pack configuration is used. Now if a default value
  is specified for a required config item in the config schema and a value for that item is not
  provided in the config, default value from config schema is used. (improvement)
* Allow user to prevent execution parameter merging when re-running an execution by passing
  ``?no_merge=true`` query parameter to the execution re-run API endpoint. (improvement)
* Add support for posixGroup to the enterprise LDAP auth backend. (improvement, bug-fix)

1.5.0 - June 24, 2016
---------------------

* SSL support for mongodb connections. (improvement)
* TriggerInstances now have statuses to help track if a TriggerInstance has been processed,
  is being processed or failed to process. This bring out some visibility into parts of the
  TriggerInstance processing pipeline and can help identify missed events. (new-feature)
* Allow user to enable service debug mode by setting ``system.debug`` config file option to
  ``True``.
  Note: This is an alternative to the existing ``--debug`` CLI flag which comes handy when running
  API services under gunicorn. (improvement)
* Fix for `data` is dropped if `message` is not present in notification. (bug-fix)
* Remove now deprecated Fabric based remote runner and corresponding
  ``ssh_runner.use_paramiko_ssh_runner`` config option. (cleanup)
* Fix support for password protected private key files in the remote runner. (bug-fix)
* Allow user to provide a path to the private SSH key file for the remote runner ``private_key``
  parameter. Previously only raw key material was supported. (improvement)
* Add new API endpoint and corresponding CLI commands (``st2 runner disable <name>``,
  ``st2 runner enable <name>``) which allows administrator to disable (and re-enable) a runner.
  (new feature)
* Add RBAC support for runner types API endpoints. (improvement)
* Allow ``register-setup-virtualenvs`` flag to be used in combination with ``register-all`` in the
  ``st2-register-content`` script.
* Add ``get_fixture_content`` method to all the base pack resource test classes. This method
  enforces fixture files location and allows user to load raw fixture content from a file on disk.
  (new feature)
  future, pack configs will be validated against the schema (if available). (new feature)
* Add data model and API changes for supporting user scoped variables. (new-feature, experimental)
* Add missing `pytz` dependency to ``st2client`` requirements file. (bug-fix)
* Fix datastore access on Python runner actions (set ``ST2_AUTH_TOKEN`` and ``ST2_API_URL`` env
  variables in Python runner actions to match sensors). (bug-fix)
* Remove support for JSON format for resource metadata files. YAML was introduced and support for
  JSON has been deprecated in StackStorm v0.6. Now the only supported metadata file format is YAML.
* Add ``-y`` / ``--yaml`` flag to the CLI ``list`` and ``get`` commands. If this flag is provided,
  command response will be formatted as YAML. (new feature)
* Alias names are now correctly scoped to a pack. This means the same name for alias can be used
  across different packs. (bug-fix)
* Ability to migrate api keys to new installs. (new feature)
* Introduce a new concept of pack config schemas. Each pack can now contain a
  ``config.schema.yaml`` file. This file can contain an optional schema for the pack config. In the
* Introduce support for pack configs which are located outside of the pack directory in
  ``/opt/stackstorm/configs/<pack name>.yaml`` files. Those files are similar to the existing pack
  configs, but in addition to the static values they can also contain dynamic values. Dynamic value
  is a value which contains a Jinja expression which is resolved to the datastore item during
  run-time. (new feature)
* Fix a regression in filtering rules by pack with CLI. (bug-fix)
* Make sure `st2-submit-debug-info` cleans up after itself and deletes a temporary directory it
  creates. (improvement) #2714
  [Kale Blankenship]
* Fix string parameter casting - leave actual ``None`` value as-is and don't try to cast it to a
  string which would fail. (bug-fix, improvement)
* Allow administrator user who's context will be used when running an action or re-running an
  action execution. (new feature)
* Add a work-around for trigger creation which would case rule creation for CronTrigger to fail
  under some circumstances. (workaround, bug-fix)
* Store action execution state transitions (event log) in the ``log`` attribute on the
  ActionExecution object. (new feature)
* Make sure ``-a all`` / ``--attr=all`` flag works for ``st2 execution list`` command (bug-fix)
* Lazily establish SFTP connection inside the remote runner when and if SFTP connection is needed.
  This way, remote runner should now also work under cygwin on Windows if SFTP related
  functionality (file upload, directory upload, etc.) is not used. (improvement)
  Reported by  Cody A. Ray
* API and CLI allow rules to be filtered by their enable state. (improvement)
* Fix SSH bastion host support by ensuring the bastion parameter is passed to the paramiko ssh
  client. (bug-fix) #2543 [Adam Mielke]
* Send out a clear error message when SSH private key is passphrase protected but user fails to
  supply passphrase with private_key when running a remote SSH action. (improvement)
* Admins will now be able pass ``--show-secrets`` when listing api keys to get the ``key_hash``
  un-masked on the CLI. (new-feature)
* Add ``--register-triggers`` flag to the ``st2-register-content`` script and ``st2ctl``.
  When this flag is provided, all triggers contained within a pack triggers directory are
  registered, consistent with the behavior of sensors, actions, etc. This feature allows users
  to register trigger types outside the scope of the sensors. (new-feature) [Cody A. Ray]

1.4.0 - April 18, 2016
----------------------

* Passphrase support for the SSH runner. (improvement)
* Improvements to ChatOps deployments of packs via ``pack deploy`` [Jon Middleton]
* Add ``extra`` field to the ActionAlias schema for adapter-specific parameters. (improvement)
* Dev environment by default now uses gunicorn to spin API and AUTH processes. (improvement)
* Allow user to pass a boolean value for the ``cacert`` st2client constructor argument. This way
  it now mimics the behavior of the ``verify`` argument of the ``requests.request`` method.
  (improvement)
* Add datastore access to Python runner actions via the ``action_service`` which is available
  to all the Python runner actions after instantiation. (new-feature) #2396 #2511
  [Kale Blankenship]
* Update ``st2actions.runners.pythonrunner.Action`` class so the constructor also takes
  ``action_service`` as the second argument.
* Allow /v1/webhooks API endpoint request body to either be JSON or url encoded form data.
  Request body type is determined and parsed accordingly based on the value of
  ``Content-Type`` header.
  Note: For backward compatibility reasons we default to JSON if ``Content-Type`` header is
  not provided. #2473 [David Pitman]
* Bug fixes to allow Sensors to have their own log files. #2487 [Andrew Regan]
* Display number of seconds which have elapsed for all the executions which have completed
  when using ``st2 execution get`` CLI command. (improvement)
* Display number of seconds elapsed for all the child tasks of a workflow action when using
  ``st2 execution get`` CLI command. (improvement)
* Various improvements in the ``linux.wait_for_ssh`` action:

  * Support for password based authentication.
  * Support for non-RSA SSH keys.
  * Support for providing a non-default (22) SSH server port.
  * Support for using default system user (stanley) ssh key if neither ``password`` nor
    ``keyfile`` parameter is provided.
* Support for leading and trailing slashes in the webhook urls. (improvement)
* Make sure that the ``filename``, ``module``, ``funcName`` and ``lineno`` attributes which are
  available in the log formatter string contain the correct values. (bug-fix)

  Reported by Andrew Regan.
* Update ``matchregex`` rule criteria operator so it uses "dot all" mode where dot (``.``)
  character will match any character including new lines. Previously ``*`` didn't match
  new lines. (improvement)
* Introduce new ``matchwildcard`` rule criteria operator. This operator provides supports for Unix
  shell-style wildcards (``*``, ``?``). (new feature)
* Allow user to pass ``verbose`` parameter to ``linux.rm`` action. For backward compatibility
  reasons it defaults to ``true``. (improvement)
* Make sure that sensor container child processes take into account ``--use-debugger`` flag passed
  to the sensor container. This fixes support for remote debugging for sensor processes. (bug-fix)
* Drop deprecated and unused ``system.admin_users`` config option which has been replaced with
  RBAC.
* Add ``--output`` and ``--existing-file`` options to ``st2-submit-debug-info``. [Kale Blankenship]
* Move stream functionality from ``st2api`` into a new standalone ``st2stream`` service. Similar to
  ``st2api`` and ``st2auth``, stream is now a standalone service and WSGI app. (improvement)
* Allow user to specify a timezone in the CLI client config (``~/.st2/config``). If the timezone is
  specified, all the timestamps displayed by the CLI will be shown in the configured timezone
  instead of a default UTC display. (new feature)
* Add ``attachments`` parameter to the ``core.sendmail`` action. (improvement) [Cody A. Ray]
* Add ``--register-setup-virtualenvs`` flag to the ``register-content`` script and ``st2ctl``.
  When this flag is provided, Python virtual environments are created for all the registered packs.
  This option is to be used with distributed setup where action runner services run on multiple
  hosts to ensure virtual environments exist on all those hosts. (new-feature)
* Update ``core.st2.CronTimer`` so it supports more of the cron-like expressions (``a-b``, ``*/a``,
  ``x,y,z``, etc.). (improvement)
* Add new ``regex`` and ``iregex`` rule criteria operator and deprecate ``matchregex`` in favor of
  those two new operators. (new-feature) [Jamie Evans]
* Record failures to enforce rules due to missing actions or parameter validation errors. A
  RuleEnforcement object will be created for failed enforcements that do not lead to an
  ActionExecution creation. (improvement)
* Add support for better serialization of the following parameter types for positional parameters
  used in the local and remote script runner actions: ``integer``, ``float``, ``boolean``,
  ``list``, ``object``. Previously those values were serialized as Python literals which made
  parsing them in the shell scripts very cumbersome. Now they are serialized based on the simple
  rules described in the documentation which makes it easy to use just by using simple shell
  primitives such as if statements and ``IFS`` for lists. (improvement, new feature)
* Fix ``linux.traceroute`` action. (bug fix)
* Fix a bug with positional argument handling in the local script runner. Now the arguments with a
  no value or value of ``None`` are correctly passed to the script. (bug fix)
* Fix rule criteria comparison and make sure that falsy criteria pattern values such as integer
  ``0`` are handled correctly. (bug-fix)

  Reported by Igor Cherkaev.
* Add ``-v`` flag (verbose mode) to the ``st2-run-pack-tests`` script. (improvement)
* The list of required and optional configuration arguments for the LDAP auth backend has changed.
  The LDAP auth backend supports other login name such as sAMAccountName. This requires a separate
  service account for the LDAP backend to query for the DN related to the login name for bind to
  validate the user password. Also, users must be in one or more groups specified in group_dns to
  be granted access.
* Mistral has deprecated the use of task name (i.e. ``$.task1``) to reference task result. It is
  replaced with a ``task`` function that returns attributes of the task such as id, state, result,
  and additional information (i.e. ``task(task1).result``).
* Add support for additional SSH key exchange algorithms to the remote runner via upgrade to
  paramiko 1.16.0. (new feature)
* Add initial code framework for writing unit tests for action aliases. For the usage, please refer
  to the "Pack Testing" documentation section. (new feature)
* For consistency rename ``deploy_pack`` alias to ``pack_deploy``.
* Fix alias executions API endpoint and make sure an exception is thrown if the user provided
  command string doesn't match the provided format string. Previously, a non-match was silently
  ignored. (bug fix)
* Add custom ``use_none`` Jinja template filter which can be used inside rules when invoking an
  action. This filter ensures that ``None`` values are correctly serialized and is to be used when
  TriggerInstance payload value can be ``None`` and ``None`` is also a valid value for a particular
  action parameter. (improvement, workaround)

1.3.2 - February 12, 2016
-------------------------

* Remove get_open_ports action from Linux pack.

1.3.1 - January 25, 2016
------------------------

* Make sure ``setup.py`` of ``st2client`` package doesn't rely on functionality which is only
  available in newer versions of pip.
* Fix an issue where trigger watcher cannot get messages from queue if multiple API processes
  are spun up. Now each trigger watcher gets its own queue and therefore there are no locking
  issues. (bug-fix)
* Dev environment by default now uses gunicorn to spin API and AUTH processes. (improvement)
* Allow user to pass a boolean value for the ``cacert`` st2client constructor argument. This way
  it now mimics the behavior of the ``verify`` argument of the ``requests.request`` method.
  (improvement)

1.3.0 - January 22, 2016
------------------------

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
* Use ``--always-copy`` option when creating virtualenv for packs from packs.setup_virtualenv
  action. This is required when st2actionrunner is kicked off from python within a virtualenv.
* Fix a bug in the remote script runner which would throw an exception if a remote script action
  caused a top level failure (e.g. copying artifacts to a remote host failed). (bug-fix)
* Display execution parameters when using ``st2 execution get <execution id>`` CLI command for
  workflow executions. (improvement)
* Fix execution cancellation for task of mistral workflow. (bug fix)
* Fix runaway action triggers caused by state miscalculation for mistral workflow. (bug fix)
* The ``--tasks`` option in the CLI for ``st2 execution get`` and ``st2 run`` will be renamed to
  ``--show-tasks`` to avoid conflict with the tasks option in st2 execution re-run.
* Add option to rerun one or more tasks in mistral workflow that has errored. (new-feature)
* Fix a bug when removing notify section from an action meta and registering it never removed
  the notify section from the db. (bug fix)
* Make sure action specific short lived authentication token is deleted immediately when execution
  is canceled. (improvement)
* Ignore lock release errors which could occur while reopening log files. This error could simply
  indicate that the lock was never acquired.
* Replace ``chatops.format_result`` with ``chatops.format_execution_result`` and remove dependency
  on st2 pack from st2contrib.
* Trace also maintains causation chain through workflows.

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
