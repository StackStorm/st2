Changelog
=========

in development
--------------

Changed
~~~~~~~

* ``st2actions.runners.pythonrunner.Action`` class path for base Python runner actions has been
  deprecated since StackStorm v1.6.0 and will be fully removed in StackStorm v2.7.0. If you have
  any actions still using this path you are encouraged to update them to use
  ``st2common.runners.base_action.Action`` path.


2.5.0 - October 25, 2017
------------------------

Added
~~~~~

* Add new feature which allows runner action output (stdout and stderr) to be streamed
  and consumed in real-time by using one of the following approaches:

  - ``/v1/executions/<execution id>/output[?type=stdout/stderr]`` API endpoint.
  - ``/v1/stream/`` stream endpoint and listening for ``st2.execution.stdout__create`` and
    ``st2.execution.output__create`` ``/v1/stream`` stream API endpoint events.
  - ``st2 execution tail <execution id> [--type=stdout/stderr]`` CLI command (underneath it uses
    stream API endpoint).

  Right now this functionality is available for the following runners:

  - local command runner
  - local script runner
  - remote command runner
  - remote script runner
  - python runner

  Note: This feature is still experimental and it's disabled by default (opt-in). To enable it,
  set ``actionrunner.stream_output`` config option to ``True``.

  (new feature) #2175 #3657 #3729
* Update ``st2 role-assignment list`` RBAC CLI command to include information about where a
  particular assignment comes from (from which local assignment or mapping file). (improvement)
  #3763
* Add support for overlapping RBAC role assignments for assignments via remote LDAP group to
  StackStorm role mappings. This means that the same role can now be granted via multiple RBAC
  mapping files.
  #3763
* Add new Jinja filters ``from_json_string``, ``from_yaml_string``, and ``jsonpath_query``.
  #3763
* Add new "Inquiry" capability, which adds ability to "ask a question", usually in a workflow.
  Create a new runner type: "inquirer" to support this, as well as new API endpoints and
  client commands for interacting with Inquiries

  Contributed by mierdin. #3653
* Added two new rule operators, `inside` and `ninside` which allow for the reverse intent of
  the `contains` and `ncontains` operators. #3781

  Contributed by @lampwins.
* Allow user to use more expressive regular expressions inside action alias format string by
  allowing them to specify start (``^``) end end (``$``) anchors. Previously, those anchors were
  automatically added at the beginning and end of the alias format string. Now they are only added
  if a format string doesn't already contain them. #3789

  Contributed by @ahubl-mz.
* Add new ``POST /v1/aliasexecution/match_and_execute`` API endpoint which allows user to
  schedule an execution based on a command string if a matching alias is found in the database.

  This API endpoint is meant to be used with chat bot plugins. It allows them to be simple thin
  wrappers around this API endpoint which send each chat line to this API endpoint and handle the
  response. #3773

Fixed
~~~~~

* Fix a bug where sensor watch queues were not deleted after sensor container process was shut
  down. This resulted in spurious queues left behind. This should not have caused performance
  impact but just messes with rabbitmqadmin output and maybe tedious for operators. (bug fix) #3628

  Reported by Igor.
* Make sure all the temporary RabbitMQ queues used by the stream service are deleted once the
  connection to RabbitMQ is closed. Those queues are temporary and unique in nature and new ones
  are created on each service start-up so we need to make sure to correctly clean up old queues.

  #3746
* Fix cancellation of subworkflow and subchain. Cancel of Mistral workflow or Action Chain is
  cascaded down to subworkflows appropriately. Cancel from tasks in the workflow or chain is
  cascaded up to the parent. (bug fix)
* Fix delays in st2resultstracker on querying workflow status from Mistral. Make sleep time for
  empty queue and no workers configurable. Reduce the default sleep times to 5 seconds. StackStorm
  instances that handle more workflows should consider increasing the query interval for better
  CPU utilization.
* Fix missing type for the parameters with enum in the core st2 packs.(bug fix) #3737

  Reported by Nick Maludy.
* Add missing ``-h`` / ``--help`` CLI flag to the following execution CLI commands: cancel, pause,
  resume. (bug fix) #3750
* Fix execution cancel and pause CLI commands and make id a required argument. (bug fix) #3750
* Fix ``st2 role-assignment list`` CLI command and allow ``--user``, ``--remote`` and ``--role``
  arguments to be used together. Previously they were mutually exclusive so it wasn't possible to
  use them together. (bug fix) #3763
* Update default event name whitelist for ``/v1/stream`` API endpoint and make sure
  ``st2.announcement__errbot`` and other event names starting with ``st2.announcement__*`` prefix
  are not filtered out. #3769 (bug fix)

  Reported by Carlos.
* Fix action-alias execute response to show execution id and matching action-alias #3231 (bug fix)
  Reported by Carlos.
* Fix ``st2 apikey load`` command to update an existing entry if items in input file contain ``id``
  attribute and item already exists on the server. This way the behavior is consistent with
  ``st2 key load`` command and the command is idempotent if each item contains ``id`` attribute.
  #3748 #3786

  Reported by Christopher Baklid.
* Don't log MongoDB database password if user specifies URI for ``database.db_host`` config
  parameter and that URI also includes a password. Default and a common scenario is specifying
  password as a separate ``database.password`` config parameter. #3797

  Reported by Igor Cherkaev.
* Fix ``POST /v1/actionalias/match`` API endpoint to correctly return a dictionary instead of an
  array. We had a correct OpenAPI definition for the response, but the code incorrectly returned
  an array instead of a dictionary.

  Note: This is a breaking change so if your code utilizes this API endpoint you need to update
  to treat response as a dictionary and not as an array with a single item. #377
* Partially fix performance overhead and regression for short and simple Python runner actions.
  Full / complete fix will be included in v2.6.0. #3809

Changed
~~~~~~~

* Minor language and style tidy up of help strings and error messages #3782 

2.4.1 - September 12, 2017
--------------------------

Fixed
~~~~~

* Fix a bug with ``/v1/packs/install`` and ``/v1/packs/uninstall`` API endpoints incorrectly using
  system user for scheduled pack install and pack uninstall executions instead of the user which
  performed the API operation.(bug fix) #3693 #3696

  Reported by theuiz.
* Fix mistral callback failure when result contains unicode. (bug fix)
* Fix cancellation of delayed action execution for tasks in workflow. (bug fix)
* Fix timeout of mistral shutdown in systemd service. The fix is done upstream.
  https://review.openstack.org/#/c/499853/ (bug fix)

Changed
~~~~~~~

* Update ``st2`` CLI command to print a more user-friendly usage / help string if no arguments are
  passed to the CLI. (improvement) #3710
* Allow user to specify multiple values for a parameter of type array of dicts when using
  ``st2 run`` CLI command. #3670

  Contributed by Hiroyasu OHYAMA.

2.4.0 - August 23, 2017
-----------------------

Added
~~~~~

* Add sample passive sensor at ``contrib/examples/sensors/echo_flask_app``. (improvement) #3667
* Add pack config into action context. This is made available under the ``config_context`` key.
  #3183
* Add limit/``-n`` flag and pagination note(stderr) in the CLI for ``st2 key list``.
  Default limit is 50. #3641
* Implement pause and resume for Mistral workflow and Action Chain. Pause and resume will cascade
  down to subworkflows and/or subchains. Pause from a subworkflow or subchain will cascade up to
  the parent workflow. (new feature)
* Add pack index endpoint. It will make a request for every index defined in st2.conf and return
  the combined list of available packs.
* Added a new field ``timestamp_f`` to the GELF logging formatter that represents
  the time of the logging even in fractional time (resolution is dependent on your
  system). This allows adjacent logging events to be distinguished more accurately
  by the time they occurred.
  Contributed by Nick Maludy (Encore Technologies) #3362
* Require new ``STREAM_VIEW`` RBAC permission type to be able to view ``/v1/stream`` stream API
  endpoint. (improvement) #3676
* Add new ``?events``, ``?action_refs`` and ``?execution_ids`` query params to ``/v1/stream/``
  API endpoint. These query parameters allow users to filter out which events to receive based
  on the event type, action ref and execution id. By default, when no filters are provided, all
  events are returned. (new feature) #3677
* Show count of pack content (actions, sensors, triggers, rules and aliases) to be registered
  before the ``st2 pack install`` so that the delay in install is not mistaken as no response
  or hanging command. (improvement) #3586 #3675
* Allow users to specify value for "array of objects" parameter type using a simple notation
  when using the ``st2 run`` CLI command. (improvement) #3646 #3670

  Contributed by Hiroyasu OHYAMA.
* Copy nearly all existing Jinja filters and make them available in both Jinja and YAQL within
  Mistral workflows (https://github.com/StackStorm/st2mistral/pull/30). Modify st2kv default
  behavior (BREAKING CHANGE) to not decrypt ciphertext in datastore by default (now explicitly
  enabled via optional parameter).

  Contributed by mierdin. #3565
* Add ``regex_substring`` Jinja filter for searching for a pattern in a provided string and
  returning the result. (improvement)

  Contributed by mierdin. #3482

Changed
~~~~~~~

* Rename ST2 action runner cancel queue from ``st2.actionrunner.canel``
  to ``st2.actionrunner.cancel``. (improvement) #3247
* Install scripts and documentation have been updated to install MongoDB 3.4 by default (previously
  3.2 was installed by default). If you want to upgrade an existing installation, please follow
  the official instructions at https://docs.mongodb.com/v3.4/release-notes/3.4-upgrade-standalone/.
  (improvement)
* Update garbage collector service to delete corresponding stdout and stderr objects which belong
  to executions which are to be deleted. #2175 #3657

Removed
~~~~~~~

* Support for pack ``config.yaml`` has been removed. Pack configuration should use the new
  style, at ``/opt/stackstorm/configs/<pack>.yaml``. Packs containing ``config.yaml`` will generate
  a fatal ERROR on pack registration.

Fixed
~~~~~

* Fix retrying in message bus exchange registration. (bug fix) #3635 #3638

  Reported by John Arnold.
* Fix message bus related race condition which could, under some rare scenarios, cause first
  published message to be ignored because there were no consumers for that particular queue yet.
  This could happen in a scenario when API service came online and served a request before action
  runner service came online.

  This also fixes an issue with Redis kombu backend not working. (bug fix) #3635 #3639 #3648
* Fix logrotate configuration to delete stale compressed st2actionrunner logs #3647
* Fix trace list API endpoint sorting by `start_timestamp`, using ``?sort_desc=True|False`` query
  parameters and by passing ``--sort=asc|desc`` parameter to the ``st2 trace list`` CLI command.
  Descending order by default.(bug fix) #3237 #3665
* Fix pack index health endpoint. It now points to the right controller. #3672
* Fix 'pack register content' failures appearing on some slower systems by lifting action timeout.
  #3685

2.3.2 - July 28, 2017
---------------------

Added
~~~~~

* Add test coverage and test timing capabilities to ``st2-run-pack-tests``.
  The ``-c`` option enables test coverage and the ``-t`` option enables test timings.
  These capabilities have also been enabled in the ci pipeline for packs in the exchange.

  Contributed by Nick Maludy. #3508
* Add ability to explicitly set ``stream_url`` in st2client. (improvement) #3432
* Add support for handling arrays of dictionaries to ``st2 config`` CLI command. (improvement)
  #3594

  Contributed by Hiroyasu OHYAMA.

Changed
~~~~~~~

* Update ``st2`` CLI so it also displays "there are more results" note when ``-n`` flag is
  used and there are more items available. (improvement) #3552

Fixed
~~~~~

* Fix st2client to display unicode characters in pack content description. (bug-fix) #3511
* Don't automatically append ``.git`` suffix to repo URIs passed to ``packs.download`` action.
  This fixes a bug and now action also works with repo urls which don't contain ``.git`` suffix.
  (bug fix)

  Contributed by carbineneutral. #3534 #3544
* st2 pack commands now work when StackStorm servers are behind a HTTP/HTTPS proxy. You can set
  ``http_proxy`` or ``https_proxy`` environment variables for ``st2api`` and ``st2actionrunner``
  processes and pack commands will work with proxy. Refer to documentation for details on
  proxy configuration. (bug-fix) #3137
* Fix API validation regression so all input data sent to some POST and PUT API endpoints is
  correctly validated. (bug fix) #3580
* Fix an API bug and allow users to create rules which reference actions which don't yet exist in
  the system when RBAC is enabled and user doesn't have system admin permission. (bug fix)
  #3572 #3573

  Reported by sibirajal.
* Add a check to make sure action exists in the POST of the action execution API. (bug fix)
* Fix api key generation, to use system user, when auth is disabled. (bug fix) #3578 #3593
* Fix invocation of Mistral workflow from Action Chain with jinja in params. (bug fix) #3440
* Fix st2client API bug, a backward incompatible change in ``query()`` method, introduced in note
  implementation (#3514) in 2.3.1. The ``query()`` method is now backward compatible (pre 2.3) and
  ``query_with_count()`` method is used for results pagination and note. #3616
* Fix logrotate script so that it no longer prints the ``st2ctl`` PID status to stdout
  for each file that it rotates. Also, it will no longer print an error if
  ``/var/log/st2/st2web.log`` is missing.

  Contributed by Nick Maludy. #3633

2.3.1 - July 07, 2017
---------------------

Added
~~~~~

* Add support for ``passphrase`` parameter to ``remote-shell-script`` runner and as such, support
  for password protected SSH key files. (improvement)

  Reported by Sibiraja L, Nick Maludy.
* Add ``json_escape`` Jinja filter for escaping JSON strings. (improvement)

  Contributed by mierdin. #3480
* Print a note to stderr if there are more entries / results on the server side which are displayed
  to the user for the following ``list`` CLI commands: ``rule``, ``execution``,
  ``rule-enforcment``, ``trace`` and ``trigger-instance``.
  Default limit is 50. (improvement)

  Reported by Eugen C. #3488

Changed
~~~~~~~

* Update ``st2 run`` / ``st2 execution run`` command to display result of workflow actions when
  they finish. In the workflow case, result of the last task (action) of the workflow is used.
  (improvement) #3481
* Update Python runner so it mimics behavior from StackStorm pre 1.6 and returns action result as
  is (serialized as string) in case we are unable to serialize action result because it contains
  non-simple types (e.g. class instances) which can't be serialized.

  In v1.6 we introduced a change when in such instances, we simply returned ``None`` as result
  and didn't log anything which was confusing. (improvement) #3489

  Reported by Anthony Shaw.
* Add missing pagination support to ``/v1/apikeys`` API endpoint. (improvement) #3486
* Update action-chain runner so a default value for ``display_published`` runner parameter is
  ``True``. This way it's consistent with Mistral runner behavior and intermediate variables
  published inside action-chain workflow are stored and displayed by default. #3518 #3519

  Reported by Jacob Floyd.
* Reduce API service (``st2api``) log clutter and log whole API response (API controller method
  return value / response body) under ``DEBUG`` log level instead of ``INFO``. (improvement) #3539

  Reported by Sibiraja L.
* Enforce validation on ``position`` parameter for action parameters. If position values are not
  sequential or not unique, action registration will now fail. (bug-fix)
  (improvement) #3317 #3474

Deprecated
~~~~~~~~~~

* Deprecate ``results_tracker`` config group and move configuration variables to ``resultstracker``
  group instead. If you have ``results_tracker`` config group in the config, it is recommended
  to switch to ``resultstracker`` instead. (bug-fix) #3500

Fixed
~~~~~

* Fix ``?name`` query param filter in ``/v1/actionalias`` API endpoint. (bug fix) #3503
* Notifier now consumes ``ActionExecution`` queue as opposed to ``LiveAction`` queue. With this
  change, the Jinja templates used in notify messages that refer to keys in ``ActionExecution``
  resolve reliably. Previously, there was a race condition in which a ``LiveAction`` would have
  been updated but ``ActionExecution`` was not and therefore, the jinja templates weren't reliably
  resolved. (bug-fix) #3487 #3496

  Reported by Chris Katzmann, Nick Maludy.
* Update config loader so it correctly handles config schema default values which are falsey
  (``False``, ``None``, ``0``, etc.) (bug-fix) #3504 #3531

  Reported by Simas Čepaitis.
* Fix ``st2ctl register`` failure to register rules in some race conditions.
  ``st2-register-content`` will now register internal trigger types by default. (bug-fix) #3542
* Correctly use service token TTL when generating temporary token for datastore service. This
  fixes a bug and allows user to set TTL value for non service tokens to less than 24 hours.
  (bug fix) #3523 #3524

  Reported by theuiz.

2.3.0 - June 19, 2017
---------------------

Added
~~~~~

* Introduce new ``CAPABILITIES`` constant on auth backend classes. With this constant, auth
  backends can advertise functionality they support (e.g. authenticate a user, retrieve information
  about a particular user, retrieve a list of groups a particular user is a member of).
  (new feature)
* Add support for automatic RBAC role assignment based on the remote auth backend groups user is a
  member of (e.g. LDAP groups) and mappings defined in ``/opt/stackstorm/rbac/mappings`` directory.

  Note: This functionality is currently implemented for enterprise LDAP auth backend and only
  available in enterprise edition.
  (new feature)
* Allow user to specify a custom list of attribute names which are masked in the log messages by
  setting ``log.mask_secrets_blacklist`` config option. (improvement)
* Add webhook payload to the Jinja render context when rendering Jinja variable inside rule
  criteria section.
* Implement RBAC for traces API endpoints. (improvement)
* Implement RBAC for ``API_KEY_CREATE`` permission type. (improvement)
* Implement RBAC for timers API endpoints. (improvement)
* Implement RBAC for webhooks get all and get one API endpoint. (improvement)
* Implement RBAC for policy types and policies get all and get one API endpoint. (improvement)
* Add new ``/v1/rbac/role_assignments`` API endpoint for retrieving user role assignment
  information. (new feature)
* Add CLI commands for listing RBAC roles:

  * ``st2 role list [--system]``
  * ``st2 role get <role id or name>``
* Add CLI commands for listing RBAC user role assignments:

  * ``st2 role-assignment list [--role=<role name>] [--user=<username>]``
  * ``st2 role-assignment get <role assignment id>``
* Add the following new actions to ``chatops`` pack:

  * ``chatops.match``
  * ``chatops.match_and_execute``
  * ``chatops.run``

  #3425 [Anthony Shaw]
* Add new ``examples.forloop_chain`` action-chain workflow to the examples pack which demonstrates
  how to iterate over multiple pages inside a workflow. #3328
  [Carles Figuerola]
* Add new ``core.uuid`` action for generating type 1 and type 4 UUIDs. [John Anderson] #3414

Changed
~~~~~~~

* Refactor the action execution asynchronous callback functionality into the runner plugin
  architecture. (improvement)
* Linux file watch sensor is now disabled by default. To enable it, set ``enabled: true`` in
  ``/opt/stackstorm/packs/linux/sensors/file_watch_sensor.yaml``
* Update the code so user can specify arbitrary default TTL for access tokens in ``st2.conf`` and
  all the StackStorm services which rely on access tokens still work.

  Previously, the lowest TTL user could specify for all the services to still work was 24 hours.
  This has been fixed and the default TTL specified in the config now only affects user access
  tokens and services use special service access tokens with no max TTL limit. (bug fix)

  Reported by Jiang Wei. #3314 #3315
* Update ``/executions/views/filters`` API endpoint so it excludes null / None from filter values
  for fields where ``null`` is not a valid field value. (improvement)

  Contributed by Cody A. Ray. #3193
* Require ``ACTION_VIEW`` permission type to be able to access entry_point and parameters actions
  view controller. (improvement)
* Update ``/v1/rbac/permission_types`` and ``/v1/rbac/permission_types/<resource type>`` API
  endpoint to return a dictionary which also includes a description for each available
  permission type. (improvement)
* Require ``EXECUTION_VIEWS_FILTERS_LIST`` RBAC permission type to be able to access
  ``/executions/views/filters`` API endpoint. (improvement)
* Add webhook payload to the Jinja render context when rendering Jinja variable inside rule criteria section
* Switch file_watch_sensor in Linux pack to use trigger type with parameters. Now you can add a
  rule with ``file_path`` and sensor will pick up the ``file_path`` from the rule. A sample rule
  is provided in ``contrib/examples/rules/sample_rule_file_watch.yaml``. (improvement)
* Cancel actions that are Mistral workflow when the parent workflow is cancelled. (improvement)
* Upgrade various internal Python library dependencies to the latest stable versions (pyyaml,
  requests, appscheduler, gitpython, paramiko, mongoengine, tooz).
* Update ``/v1/rbac/roles`` API endpoint so it includes corresponding permission grant objects.
  Previously it only included permission grant ids. (improvement)
* When RBAC is enabled and action is scheduled (ran) through the API, include ``rbac`` dictionary
  with ``user`` and ``roles`` ``action_context`` attribute. (improvement)
* Make the query interval to third party workflow systems (including mistral) a configurable
  value. You can now set ``query_interval`` in ``[results_tracker]`` section in ``/etc/st2/st2.conf``.
  With this, the default query interval is set to 20s as opposed to 0.1s which was rather aggressive
  and could cause CPU churn when there is a large number of outstanding workflows. (improvement)
* Let ``st2 pack install`` register all available content in pack by default to be consistent with
  ``st2 pack register``. (improvement) #3452
* The ``dest_server`` parameter has been removed from the ``linux.scp`` action. Going forward simply
  specify the server as part of the ``source`` and / or ``destination`` arguments. (improvement)
  #3335 #3463 [Nick Maludy]
* Add missing database indexes which should speed up various queries on production deployments with
  large datasets. (improvement)
* Use a default value for a config item from config schema even if that config item is not required
  (``required: false``). (improvement)

  Reported by nmlaudy. #3468 #3469
* Removing empty ``config.yaml`` for packs pack so warning isn't thrown by default now that deprecation
  warning is in place. (improvement)

Removed
~~~~~~~

* Drop support for invalid semver versions strings (e.g. ``2.0``) in pack.yaml pack metadata. Only
  full semver version strings are supported, e.g. ``2.1.1``. This was originally deprecated in
  v2.1.0.

Deprecated
~~~~~~~~~~

* Packs containing ``config.yaml`` will now generate a WARNING log on pack registration. Support for
  ``config.yaml`` will be removed in StackStorm 2.4. Migrate your pack configurations now.

Fixed
~~~~~

* Update st2rulesengine to exit non-0 on failure (bug fix) #3394 [Andrew Regan]
* Fix a bug where trigger parameters and payloads were being validated regardless of the relevant settings
  in the configuration (``system.validate_trigger_payload``, ``system.validate_trigger_parameters``). (bug fix)
* Fix ``system=True`` filter in the ``/v1/rbac/roles`` API endpoint so it works correctly. (bug fix)
* Fix a bug where keyvalue objects weren't properly cast to numeric types. (bug fix)
* When action worker is being shutdown and action executions are being abandoned, invoke post run
  on the action executions to ensure operations such as callback is performed. (bug fix)
* Fix action chain runner workflows so variables (vars) and parameter values
  support non-ascii (unicode) characters. (bug fix)
* Fix a bug in query base module when outstanding queries to mistral or other workflow engines
  could cause a tight loop without cooperative yield leading to 100% CPU usage by st2resultstracker
  process. (bug-fix)
* Ignore unicode related encoding errors which could occur in some circumstances when
  ``packs.setup_virtualenv`` fails due to a missing dependency or similar. (improvement, bug fix)
  #3337 [Sean Reifschneider]
* Update ``st2-apply-rbac-definitions`` so it also removes assignments for users which don't exist
  in the database. (improvement, bug fix)
* Fix a bug where action runner throws KeyError on abandoning action executions
  during process shutdown. (bug fix)
* Fix URL parsing bug where percent encoded URLs aren't decoded properly (bug fix)
* The API endpoint for searching or showing packs has been updated to return an empty list
  instead of ``None`` when the pack was not found in the index. (bug fix)

Security
~~~~~~~~

* Make sure all the role assignments for a particular user are correctly deleted from the database
  after deleting an assignment file from ``/opt/stackstorm/rbac/assignments`` directory and running
  ``st2-apply-rbac-definitions`` tool. (bug fix)


2.2.1 - April 3, 2017
---------------------

Added
~~~~~

* Allow user to specify which branch of ``st2tests`` repository to use by passing ``-b`` option to
  ``st2-self-check`` script. (improvement)
* Update ``tooz`` library to the latest version (v1.15.0). Using the latest version means
  StackStorm now also supports using ``consul``, ``etcd`` and other new backends supported by
  tooz for coordination. (improvement)

Fixed
~~~~~

* Fix ``st2ctl reload`` command so it preserves exit code from `st2-register-content` script and
  correctly fails on failure by default.
* Fix base action alias test class (``BaseActionAliasTestCase``) so it also works if the local pack
  directory name doesn't match the pack name (this might be the case with new pack management
  during development where local git repository directory name doesn't match pack name) (bug fix)
* Fix a bug with default values from pack config schema not being passed via config to Python
  runner actions and sensors if pack didn't contain a config file in ``/opt/stackstorm/configs``
  directory. (bug fix)

  Reported by Jon Middleton.
* Make various improvements and changes to ``st2-run-pack-tests`` script so it works out of the box
  on servers where StackStorm has been installed using packages. (improvement)
* Fix a bug with authentication middleware not working correctly when supplying credentials in an
  Authorization header using basic auth format when password contained a colon (``:``).

  Note: Usernames with colon are still not supported. (bug fix)

  Contributed by Carlos.
* Update ``st2-run-pack-tests`` script so it doesn't try to install global pack test dependencies
  (mock, unittest2, nose) when running in an environment where those dependencies are already
  available.
* Make sure remote command and script runner correctly close SSH connections after the action
  execution has completed. (bug fix)

  Reported by Nagy Krisztián.
* Fix a bug with pack configs API endpoint (``PUT /v1/configs/``) not working when RBAC was
  enabled. (bug fix)

  Reported by efenian.
* Fix concurrency related unit tests to support upgrade of the tooz library. (bug fix)
* Fix a bug with config schema validation not being performed upon registration which could cause
  bad or empty config schema to end up in the system. (bug fix)

Security
~~~~~~~~

* Removed support for medium-strength ciphers from default nginx configuration (#3244)
* Various security related improvements in the enterprise LDAP auth backend. (improvement,
  bug fix)


2.2.0 - February 27, 2017
-------------------------

Added
~~~~~

* Use the newly introduced CANCELLED state in mistral for workflow cancellation. Currently, st2
  put the workflow in a PAUSED state in mistral. (improvement)
* Add support for evaluating Jinja expressions in mistral workflow definition where yaql
  expressions are typically accepted. (improvement)
* Update the dependencies and the code base so we now also support MongoDB 3.4. Officially
  supported MongoDB versions are now MongoDB 3.2 and 3.4. Currently default version installed by
  the installer script still is 3.2. (improvement)
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
* Add support for `st2 login` and `st2 whoami` commands. These add some additional functionality
  beyond the existing `st2 auth` command and actually works with the local configuration so that
  users do not have to.
* Add support for complex rendering inside of array and object types. This allows the user to
  nest Jinja variables in array and object types.
* Add new ``-j`` flag to the ``st2-run-pack-tests`` script. When this flag is specified script will
  just try to run the tests and it won't set up the virtual environment and install the
  dependencies. This flag can be used when virtual environment for pack tests already exists and
  when you know dependencies are already installed and up to date. (new feature)

Changed
~~~~~~~

* Mistral fork is updated to match the master branch at OpenStack Mistral. (improvement)
* Update Python runner to throw a more user-friendly exception in case action metadata file
  references a script file which doesn't exist or which contains invalid syntax. (improvement)
* Update ``st2auth`` service so it includes more context and throws a more user-friendly exception
  when retrieving an auth backend instance fails. This makes it easier to debug and spot various
  auth backend issues related to typos, misconfiguration and similar. (improvement)
* Let querier plugin decide whether to delete state object on error. Mistral querier will
  delete state object on workflow completion or when the workflow or task references no
  longer exists. (improvement)`

Removed
~~~~~~~

* ``{{user.}}`` and ``{{system.}}`` notations to access user and system
  scoped items from datastore are now unsupported. Use  ``{{st2kv.user.}}``
  and ``{{st2kv.system.}}`` instead. Please update all your content (actions, rules and
  workflows) to use the new notation. (improvement)

Fixed
~~~~~

* Fix returning a tuple from the Python runner so it also works correctly, even if action returns
  a complex type (e.g. Python class instance) as a result. (bug fix)

  Reported by skjbulcher #3133
* Fix a bug with ``packs.download`` action and as such as ``pack install`` command not working with
  git repositories which used a default branch which was not ``master``. (bug fix)
* Fix a bug with not being able to apply some global permission types (permissions which are global
  and not specific to a resource) such as pack install, pack remove, pack search, etc. to a role
  using ``st2-apply-rbac-definitions``. (bug fix)

* Fix ``/v1/packs/views/files/<pack ref or id>`` and
  ``/v1/packs/views/file/<pack ref or id>/<file path>`` API endpoint so it
  works correctly for packs where pack name is not equal to the pack ref. (bug fix)

  Reported by skjbulcher #3128
* Improve binary file detection and fix "pack files" API controller so it works correctly for
  new-style packs which are also git repositories. (bug fix)
* Fix cancellation specified in concurrency policies to cancel actions appropriately. Previously,
  mistral workflow is orphaned and left in a running state. (bug fix)
* If a retry policy is defined, action executions under the context of a workflow will not be
  retried on timeout or failure. Previously, action execution will be retried but workflow is
  terminated. (bug fix)
* Fix how mistral client and resource managers are being used in the mistral runner. Authentication
  has changed in the mistral client. Fix unit test accordingly. (bug fix)
* Fix issue where passing a single integer member for an array parameter for an action would
  cause a type mismatch in the API (bug fix)
* Fix ``--config-file`` st2 CLI argument not correctly expanding the provided path if the path
  contained a reference to the user home directory (``~``, e.g. ``~/.st2/config.ini``) (bug fix)
* Fix action alias update API endpoint. (bug fix)
* Fix a bug with ``--api-token`` / ``-t`` and other CLI option values not getting correctly
  propagated to all the API calls issued in the ``st2 pack install``, ``st2 pack remove`` and
  ``st2 pack config`` commands. (bug fix)


2.1.1 - December 16, 2016
-------------------------

Added
~~~~~

* ``core.http`` action now also supports HTTP basic auth and digest authentication by passing
  ``username`` and ``password`` parameter to the action. (new feature)
* After running ``st2 pack install`` CLI command display which packs have been installed.
  (improvement)

Changed
~~~~~~~

* Update ``/v1/packs/register`` API endpoint so it throws on failure (e.g. invalid pack or resource
  metadata). This way the default behavior is consistent with default
  ``st2ctl reload --register-all`` behavior.
  If user doesn't want the API endpoint to fail on failure, they can pass
  ``"fail_on_failure": false`` attribute in the request payload. (improvement)
* Throw a more user-friendly exception when registering packs (``st2ctl reload``) if pack ref /
  name is invalid. (improvement)
* Update ``packs.load`` action to also register triggers by default. (improvement)

Fixed
~~~~~

* Fix ``GET /v1/packs/<pack ref or id>`` API endpoint - make sure pack object is correctly returned
  when pack ref doesn't match pack name. Previously, 404 not found was thrown. (bug fix)
* Update local action runner so it supports and works with non-ascii (unicode) parameter keys and
  values. (bug fix)

  Contribution by Hiroyasu OHYAMA. #3116
* Update ``/v1/packs/register`` API endpoint so it registers resources in the correct order which
  is the same as order used in ``st2-register-content`` script. (bug fix)


2.1.0 - December 05, 2016
-------------------------

Added
~~~~~

* New pack management:

  - Add new ``stackstorm_version`` and ``system`` fields to the pack.yaml metadata file. Value of
    the first field can contain a specific StackStorm version with which the pack is designed to
    work with (e.g. ``>=1.6.0,<2.2.0`` or ``>2.0.0``). This field is checked when installing /
    registering a pack and installation is aborted if pack doesn't support the currently running
    StackStorm version. Second field can contain an object with optional system / OS level
    dependencies. (new feature)
  - Add new ``contributors`` field to the pack metadata file. This field can contain a list of
    people who have contributed to the pack. The format is ``Name <email>``, e.g.
    ``Tomaz Muraus <tomaz@stackstorm.com>`` (new feature)
  - Add support for default values and dynamic config values for nested config objects.
    (new feature, improvement)
  - Add new ``st2-validate-pack-config`` tool for validating config file against a particular
    config schema file. (new-feature)

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
* Allow user to supply multiple resource ids using ``?id`` query parameter when filtering
  "get all" API endpoint result set (e.g. `?id=1,2,3,4`). This allows for a better client and
  servers performance when user is polling and interested in multiple resources such as polling on
  multiple action executions. (improvement)
* Add support for ssh config file for ParamikoSSHrunner. Now ``ssh_config_file_path`` can be set
  in st2 config and can be used to access remote hosts when ``use_ssh_config`` is set to
  ``True``. However, to access remote hosts, action parameters like username and
  password/private_key, if provided with action, will have precedence over the config file
  entry for the host. #2941 #3032 #3058 [Eric Edgar] (improvement)


Changed
~~~~~~~

* Improved pack validation - now when the packs are registered we check that:

  - ``version`` attribute in the pack metadata file matches valid semver format (e.g
    ``0.1.0``, ``2.0.0``, etc.)
  - ``email`` attribute (if specified) contains a valid email address. (improvement)
  - Only valid word characters (``a-z``, ``0-9`` and ``_``) used for action parameter
    names. Previously, due to bug in the code, any character was allowed.

  If validation fails, pack registration will fail. If you have an existing action or pack
  definition which uses invalid characters, pack registration will fail. **You must update
  your packs**.
* For consistency with new pack name validation changes, sample ``hello-st2`` pack has been
  renamed to ``hello_st2``.
* Update ``packs.install`` action (``pack install`` command) to only load resources from the
  packs which are being installed. Also update it and remove "restart sensor container" step from
  the install workflow. This step hasn't been needed for a while now because sensor container
  dynamically reads a list of available sensors from the database and starts the sub processes.
  (improvement)
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
* Upgrade various internal Python library dependencies to the latest stable versions (gunicorn,
  kombu, six, appscheduler, passlib, python-gnupg, semver, paramiko, python-keyczar, virtualenv).

Removed
~~~~~~~

* Remove ``packs.info`` action because ``.gitinfo`` file has been deprecated with the new pack
  management approach. Now pack directories are actual checkouts of the corresponding pack git
  repositories so this file is not needed anymore.

Fixed
~~~~~

* Fix ``packs.uninstall`` action so it also deletes ``configs`` and ``policies`` which belong to
    the pack which is being uninstalled. (bug fix)
* When a policy cancels a request due to concurrency, it leaves end_timestamp set to None which
  the notifier expects to be a date. This causes an exception in "isotime.format()". A patch was
  released that catches this exception, and populates payload['end_timestamp'] with the equivalent
  of "datetime.now()" when the exception occurs.
* Adding check for datastore Client expired tokens used in sensor container
* Fix python action runner actions and make sure that modules from ``st2common/st2common/runners``
  directory don't pollute ``PYTHONPATH`` for python runner actions. (bug fix)

2.0.1 - September 30, 2016
--------------------------

Added
~~~~~

* Allow users to specify sort order when listing traces using the API endpoint by specifying
  ``?sort_desc=True|False`` query parameters and by passing ``--sort=asc|desc`` parameter to
  the ``st2 trace list`` CLI command. (improvement)
* Retry connecting to RabbitMQ on services start-up if connecting fails because
  of an intermediate network error or similar. (improvements)
* Allow jinja expressions ``{{st2kv.system.foo}}`` and ``{{st2kv.user.foo}}`` to access
  datastore items from workflows, actions and rules. This is in addition to supporting
  expressions ``{{system.foo}}`` and ``{{user.foo}}``.

Changed
~~~~~~~

* Update traces list API endpoint and ``st2 trace list`` so the traces are sorted by
  ``start_timestamp`` in descending order by default. This way it's consistent with executions
  list and ``-n`` CLI parameter works as expected. (improvement)

Deprecated
~~~~~~~~~~

* In subsequent releases, the expressions ``{{system.}}`` and ``{{user.}}`` for accessing
  datastore items will be deprecated. It is recommended to switch to using
  ``{{st2kv.system.}}`` and ``{{st2kv.user.}}`` for your content. (improvement)

Fixed
~~~~~

* Fix ``st2 execution get`` command so now ``--attr`` argument correctly works with child
  properties of the ``result`` and ``trigger_instance`` dictionary (e.g. ``--attr
  result.stdout result.stderr``). (bug fix)
* Fix a bug with action default parameter values not supporting Jinja template
  notation for parameters of type ``object``. (bug fix, improvement)
* Fix ``--user`` / ``-u`` argument in the ``st2 key delete`` CLI command.


2.0.0 - August 31, 2016
-----------------------

Added
~~~~~

* Implement custom Jinja filter functions ``to_json_string``, ``to_yaml_string``,
  ``to_human_time_from_seconds`` that can be used in actions and workflows. (improvement)
* Default chatops message to include time taken to complete an execution. This uses
  ``to_human_time_from_seconds`` function. (improvement)
* Allow user to cancel multiple executions using a single invocation of ``st2 execution cancel``
  command by passing multiple ids to the command -
  ``st2 execution cancel <id 1> <id 2> <id n>`` (improvement)
* We now execute --register-rules as part of st2ctl reload. PR raised by Vaishali:
  https://github.com/StackStorm/st2/issues/2861#issuecomment-239275641
* Update ``packs.uninstall`` command to print a warning message if any rules in the system
  reference a trigger from a pack which is being uninstalled. (improvement)
* Allow user to list and view rules using the API even if a rule in the database references a
  non-existent trigger. This shouldn't happen during normal usage of StackStorm, but it makes it
  easier for the user to clean up in case database ends up in a inconsistent state. (improvement)

Changed
~~~~~~~

* Refactor Jinja filter functions into appropriate modules. (improvement)
* Bump default timeout for ``packs.load`` command from ``60`` to ``100`` seconds. (improvement)
* Upgrade pip and virtualenv libraries used by StackStorm pack virtual environments to the latest
  versions (8.1.2 and 15.0.3).
* Change Python runner action and sensor Python module loading so the module is still loaded even if
  the module name clashes with another module which is already in ``PYTHONPATH``
  (improvement)

Fixed
~~~~~

* Fix a bug when jinja templates with filters (for example,
  ``st2 run core.local cmd='echo {{"1.6.0" | version_bump_minor}}'``) in parameters wasn't rendered
  correctly when executing actions. (bug-fix)
* Fix validation of the action parameter ``type`` attribute provided in the YAML metadata.
  Previously we allowed any string value, now only valid types (object, string, number,
  integer, array, null) are allowed. (bug fix)
* Fix disabling and enabling of a sensor through an API and CLI. (bug-fix)
* Fix HTTP runner so it works correctly when body is provided with newer versions of requests
  library (>= 2.11.0). (bug-fix) #2880

  Contribution by Shu Sugimoto.

1.6.0 - August 8, 2016
----------------------

Added
~~~~~

* Allow user to specify an action which is performed on an execution (``delay``, ``cancel``) when a
  concurrency policy is used and a defined threshold is reached. For backward compatibility,
  ``delay`` is the default behavior, but now users can also specify ``cancel`` and an execution will
  be canceled instead of delayed when a threshold is reached.
* Add support for sorting execution list results, allowing access to oldest items. (improvement)
* Allow administrator to configure maximum limit which can be specified using ``?limit``
  query parameters when making API calls to get all / list endpoints. For backward compatibility
  and safety reasons, the default value still is ``100``. (improvement)
* Include a chatops alias sample in ``examples`` pack that shows how to use ``format`` option to
  display chatops messages in custom formatted way. (improvement)
* Include a field ``elapsed_seconds`` in execution API response for GET calls. The clients using
  the API can now use ``elapsed_seconds`` without having to repeat computation. (improvement)
* Implement custom YAQL function ``st2kv`` in Mistral to get key-value pair from StackStorm's
  datastore. (new-feature)

Changed
~~~~~~~

* Upgrade to pymongo 3.2.2 and mongoengine 0.10.6 so StackStorm now also supports and works with
  MongoDB 3.x. (improvement)
* Update action runner to use two internal green thread pools - one for regular (non-workflow) and
  one for workflow actions. Both pool sizes are user-configurable. This should help increase the
  throughput of a single action runner when the system is not over-utilized. It can also help
  prevent deadlocks which may occur when using delay policies with action-chain workflows.
  (improvement)
* Update CLI commands to make sure that all of them support ``--api-key`` option. (bug-fix)
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
* Include testing for chatops ``format_execution_result`` python action. The tests cover various
  action types. (improvement)
* Update ``st2-register-content`` script so it validates new style configs in
  ``/opt/stackstorm/configs/`` directory when using ``--register-configs`` flag if a pack contains
  a config schema (``config.schema.yaml``). (improvement)

Fixed
~~~~~

* Make sure policies which are disabled are not applied. (bug fix)
  Reported by Brian Martin.
* Fix ``Internal Server Error`` when an undefined jinja variable is used in action alias ack field.
  We now send a http status code ``201`` but also explicitly say we couldn't render the ``ack``
  field. The ``ack`` is anyways a nice-to-have message which is not critical. Previously, we still
  kicked off the execution but sent out ``Internal Server Error`` which might confuse the user
  whether execution was kicked off or not. (bug-fix)


1.5.1 - July 13, 2016
---------------------

Added
~~~~~

* Add support for default values when a new pack configuration is used. Now if a default value
  is specified for a required config item in the config schema and a value for that item is not
  provided in the config, default value from config schema is used. (improvement)
* Add support for posixGroup to the enterprise LDAP auth backend. (improvement, bug-fix)

Changed
~~~~~~~

* Allow user to prevent execution parameter merging when re-running an execution by passing
  ``?no_merge=true`` query parameter to the execution re-run API endpoint. (improvement)

Fixed
~~~~~

* Fix trigger registration when using st2-register-content script with ``--register-triggers``
  flag. (bug-fix)
* Fix an issue with CronTimer sometimes not firing due to TriggerInstance creation failure.
  (bug-fix)
  Reported by Cody A. Ray


1.5.0 - June 24, 2016
---------------------

Added
~~~~~

* TriggerInstances now have statuses to help track if a TriggerInstance has been processed,
  is being processed or failed to process. This bring out some visibility into parts of the
  TriggerInstance processing pipeline and can help identify missed events. (new-feature)
* Allow user to enable service debug mode by setting ``system.debug`` config file option to
  ``True``.
  Note: This is an alternative to the existing ``--debug`` CLI flag which comes handy when running
  API services under gunicorn. (improvement)
* Add new API endpoint and corresponding CLI commands (``st2 runner disable <name>``,
  ``st2 runner enable <name>``) which allows administrator to disable (and re-enable) a runner.
  (new feature)
* Add RBAC support for runner types API endpoints. (improvement)
* Add ``get_fixture_content`` method to all the base pack resource test classes. This method
  enforces fixture files location and allows user to load raw fixture content from a file on disk.
  (new feature)
  future, pack configs will be validated against the schema (if available). (new feature)
* Add data model and API changes for supporting user scoped variables. (new-feature, experimental)
* Add ``-y`` / ``--yaml`` flag to the CLI ``list`` and ``get`` commands. If this flag is provided,
  command response will be formatted as YAML. (new feature)
* Ability to migrate api keys to new installs. (new feature)
* Introduce a new concept of pack config schemas. Each pack can now contain a
  ``config.schema.yaml`` file. This file can contain an optional schema for the pack config.
  Site-specific pack configuration is then stored outside the pack directory, in
  ``/opt/stackstorm/configs/<pack name>.yaml``. Those files are similar to the existing pack
  configs, but in addition to the static values they can also contain dynamic values. Dynamic value
  is a value which contains a Jinja expression which is resolved to a datastore item during
  run-time. (new feature)
* Allow administrator user whose context will be used when running an action or re-running an
  action execution. (new feature)
* Store action execution state transitions (event log) in the ``log`` attribute on the
  ActionExecution object. (new feature)
* Admins will now be able pass ``--show-secrets`` when listing api keys to get the ``key_hash``
  un-masked on the CLI. (new-feature)
* Add ``--register-triggers`` flag to the ``st2-register-content`` script and ``st2ctl``.
  When this flag is provided, all triggers contained within a pack triggers directory are
  registered, consistent with the behavior of sensors, actions, etc. This feature allows users
  to register trigger types outside the scope of the sensors. (new-feature) [Cody A. Ray]

Changed
~~~~~~~

* Lazily establish SFTP connection inside the remote runner when and if SFTP connection is needed.
  This way, remote runner should now also work under cygwin on Windows if SFTP related
  functionality (file upload, directory upload, etc.) is not used. (improvement)
  Reported by  Cody A. Ray
* API and CLI allow rules to be filtered by their enable state. (improvement)
* Send out a clear error message when SSH private key is passphrase protected but user fails to
  supply passphrase with private_key when running a remote SSH action. (improvement)

Removed
~~~~~~~

* Remove now deprecated Fabric based remote runner and corresponding
  ``ssh_runner.use_paramiko_ssh_runner`` config option. (cleanup)
* Remove support for JSON format for resource metadata files. YAML was introduced and support for
  JSON has been deprecated in StackStorm v0.6. Now the only supported metadata file format is YAML.

Fixed
~~~~~

* Fix for ``data` is dropped if ``message`` is not present in notification. (bug-fix)
* Fix support for password protected private key files in the remote runner. (bug-fix)
* Allow user to provide a path to the private SSH key file for the remote runner ``private_key``
  parameter. Previously only raw key material was supported. (improvement)
* Allow ``register-setup-virtualenvs`` flag to be used in combination with ``register-all`` in the
  ``st2-register-content`` script.
* Add missing `pytz` dependency to ``st2client`` requirements file. (bug-fix)
* Fix datastore access on Python runner actions (set ``ST2_AUTH_TOKEN`` and ``ST2_API_URL`` env
  variables in Python runner actions to match sensors). (bug-fix)
* Alias names are now correctly scoped to a pack. This means the same name for alias can be used
  across different packs. (bug-fix)
* Fix a regression in filtering rules by pack with CLI. (bug-fix)
* Make sure `st2-submit-debug-info` cleans up after itself and deletes a temporary directory it
  creates. (improvement) #2714
  [Kale Blankenship]
* Fix string parameter casting - leave actual ``None`` value as-is and don't try to cast it to a
  string which would fail. (bug-fix, improvement)
* Add a work-around for trigger creation which would case rule creation for CronTrigger to fail
  under some circumstances. (workaround, bug-fix)
* Make sure ``-a all`` / ``--attr=all`` flag works for ``st2 execution list`` command (bug-fix)
* Fix SSH bastion host support by ensuring the bastion parameter is passed to the paramiko ssh
  client. (bug-fix) #2543 [Adam Mielke]

Security
~~~~~~~~

* SSL support for mongodb connections. (improvement)


1.4.0 - April 18, 2016
----------------------

Added
~~~~~

* Passphrase support for the SSH runner. (improvement)
* Add ``extra`` field to the ActionAlias schema for adapter-specific parameters. (improvement)
* Allow user to pass a boolean value for the ``cacert`` st2client constructor argument. This way
  it now mimics the behavior of the ``verify`` argument of the ``requests.request`` method.
  (improvement)
* Add datastore access to Python runner actions via the ``action_service`` which is available
  to all the Python runner actions after instantiation. (new-feature) #2396 #2511
  [Kale Blankenship]
* Update ``st2actions.runners.pythonrunner.Action`` class so the constructor also takes
  ``action_service`` as the second argument.
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
* Introduce new ``matchwildcard`` rule criteria operator. This operator provides supports for Unix
  shell-style wildcards (``*``, ``?``). (new feature)
* Allow user to pass ``verbose`` parameter to ``linux.rm`` action. For backward compatibility
  reasons it defaults to ``true``. (improvement)
* Add ``--output`` and ``--existing-file`` options to ``st2-submit-debug-info``. [Kale Blankenship]
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
* Add support for better serialization of the following parameter types for positional parameters
  used in the local and remote script runner actions: ``integer``, ``float``, ``boolean``,
  ``list``, ``object``. Previously those values were serialized as Python literals which made
  parsing them in the shell scripts very cumbersome. Now they are serialized based on the simple
  rules described in the documentation which makes it easy to use just by using simple shell
  primitives such as if statements and ``IFS`` for lists. (improvement, new feature)
* Add ``-v`` flag (verbose mode) to the ``st2-run-pack-tests`` script. (improvement)
* Add support for additional SSH key exchange algorithms to the remote runner via upgrade to
  paramiko 1.16.0. (new feature)
* Add initial code framework for writing unit tests for action aliases. For the usage, please refer
  to the "Pack Testing" documentation section. (new feature)
* Add custom ``use_none`` Jinja template filter which can be used inside rules when invoking an
  action. This filter ensures that ``None`` values are correctly serialized and is to be used when
  TriggerInstance payload value can be ``None`` and ``None`` is also a valid value for a particular
  action parameter. (improvement, workaround)

Changed
~~~~~~~

* Improvements to ChatOps deployments of packs via ``pack deploy`` [Jon Middleton]
* Allow ``/v1/webhooks`` API endpoint request body to either be JSON or url encoded form data.
  Request body type is determined and parsed accordingly based on the value of
  ``Content-Type`` header.
  Note: For backward compatibility reasons we default to JSON if ``Content-Type`` header is
  not provided. #2473 [David Pitman]
* Update ``matchregex`` rule criteria operator so it uses "dot all" mode where dot (``.``)
  character will match any character including new lines. Previously ``*`` didn't match
  new lines. (improvement)
* Move stream functionality from ``st2api`` into a new standalone ``st2stream`` service. Similar to
  ``st2api`` and ``st2auth``, stream is now a standalone service and WSGI app. (improvement)
* Record failures to enforce rules due to missing actions or parameter validation errors. A
  RuleEnforcement object will be created for failed enforcements that do not lead to an
  ActionExecution creation. (improvement)
* The list of required and optional configuration arguments for the LDAP auth backend has changed.
  The LDAP auth backend supports other login name such as sAMAccountName. This requires a separate
  service account for the LDAP backend to query for the DN related to the login name for bind to
  validate the user password. Also, users must be in one or more groups specified in group_dns to
  be granted access.
* For consistency rename ``deploy_pack`` alias to ``pack_deploy``.

Deprecated
~~~~~~~~~~

* Drop deprecated and unused ``system.admin_users`` config option which has been replaced with
  RBAC.
* The ``matchregex`` rule criteria operator has been deprecated in favor of ``regex`` and
  ``iregex``.
* Mistral has deprecated the use of task name (i.e. ``$.task1``) to reference task result. It is
  replaced with a ``task`` function that returns attributes of the task such as id, state, result,
  and additional information (i.e. ``task(task1).result``).

Fixed
~~~~~

* Bug fixes to allow Sensors to have their own log files. #2487 [Andrew Regan]
* Make sure that the ``filename``, ``module``, ``funcName`` and ``lineno`` attributes which are
  available in the log formatter string contain the correct values. (bug-fix)

  Reported by Andrew Regan.
* Make sure that sensor container child processes take into account ``--use-debugger`` flag passed
  to the sensor container. This fixes support for remote debugging for sensor processes. (bug-fix)
* Fix ``linux.traceroute`` action. (bug fix)
* Fix a bug with positional argument handling in the local script runner. Now the arguments with a
  no value or value of ``None`` are correctly passed to the script. (bug fix)
* Fix rule criteria comparison and make sure that false criteria pattern values such as integer
  ``0`` are handled correctly. (bug-fix)

  Reported by Igor Cherkaev.
* Fix alias executions API endpoint and make sure an exception is thrown if the user provided
  command string doesn't match the provided format string. Previously, a non-match was silently
  ignored. (bug fix)

1.3.2 - February 12, 2016
-------------------------

Removed
~~~~~~~

* Remove ``get_open_ports`` action from Linux pack.


1.3.1 - January 25, 2016
------------------------

Changed
~~~~~~~

* Dev environment by default now uses gunicorn to spin API and AUTH processes. (improvement)
* Allow user to pass a boolean value for the ``cacert`` st2client constructor argument. This way
  it now mimics the behavior of the ``verify`` argument of the ``requests.request`` method.
  (improvement)

Fixed
~~~~~

* Make sure ``setup.py`` of ``st2client`` package doesn't rely on functionality which is only
  available in newer versions of pip.
* Fix an issue where trigger watcher cannot get messages from queue if multiple API processes
  are spun up. Now each trigger watcher gets its own queue and therefore there are no locking
  issues. (bug-fix)


1.3.0 - January 22, 2016
------------------------

Added
~~~~~

* Allow user to pass ``env`` parameter to ``packs.setup_virtualenv`` and ``packs.install``
  action.

  This comes in handy if a user wants pip to use an HTTP(s) proxy (HTTP_PROXY and HTTPS_PROXY
  environment variable) when installing pack dependencies. (new feature)
* Ability to view causation chains in Trace. This helps reduce the noise when using Trace to
  identify specific issues. (new-feature)
* Filter Trace components by model types to only view ActionExecutions, Rules or TriggerInstances.
  (new-feature)
* Include ref of the most meaningful object in each trace component. (new-feature)
* Ability to hide trigger-instance that do not yield a rule enforcement. (new-feature)
* Action and Trigger filters for rule list (new-feature)
* Add ``--register-fail-on-failure`` flag to ``st2-register-content`` script. If this flag is
  provided, the script will fail and exit with non-zero status code if registering some resource
  fails. (new feature)
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
* Add option to rerun one or more tasks in mistral workflow that has errored. (new-feature)

Changed
~~~~~~~

* Change the rule list columns in the CLI from ref, pack, description and enabled to ref,
  trigger.ref, action.ref and enabled. This aligns closer the UI and also brings important
  information front and center. (improvement)
* Support for object already present in the DB for ``st2-rule-tester`` (improvement)
* Throw a more friendly error message if casting parameter value fails because the value contains
  an invalid type or similar. (improvement)
* Display execution parameters when using ``st2 execution get <execution id>`` CLI command for
  workflow executions. (improvement)
* The ``--tasks`` option in the CLI for ``st2 execution get`` and ``st2 run`` will be renamed to
  ``--show-tasks`` to avoid conflict with the tasks option in st2 execution re-run.
* Replace ``chatops.format_result`` with ``chatops.format_execution_result`` and remove dependency
  on st2 pack from st2contrib.
* Trace also maintains causation chain through workflows.

Deprecated
~~~~~~~~~~

* Deprecated ``params`` action attribute in the action chain definition in favor of the new
  ``parameters`` attribute. (improvement)

Fixed
~~~~~

* Add missing logrotate config entry for ``st2auth`` service. #2294 [Vignesh Terafast]
* Add a missing ``get_logger`` method to the `MockSensorService``. This method now returns an
  instance of ``Mock`` class which allows user to assert that a particular message has been
  logged. [Tim Ireland, Tomaz Muraus]
* Fix validation error when None is passed explicitly to an optional argument on action
  execution. (bug fix)
* Fix action parameters validation so that only a selected set of attributes can be overriden for
  any runner parameters. (bug fix)
* Fix type in the headers parameter for the http-request runner. (bug fix)
* Fix runaway action triggers caused by state miscalculation for mistral workflow. (bug fix)
* Use ``--always-copy`` option when creating virtualenv for packs from packs.setup_virtualenv
  action. This is required when st2actionrunner is kicked off from python within a virtualenv.
* Fix a bug in the remote script runner which would throw an exception if a remote script action
  caused a top level failure (e.g. copying artifacts to a remote host failed). (bug-fix)
* Fix execution cancellation for task of mistral workflow. (bug fix)
* Fix runaway action triggers caused by state miscalculation for mistral workflow. (bug fix)
* Fix a bug when removing notify section from an action meta and registering it never removed
  the notify section from the db. (bug fix)
* Make sure action specific short lived authentication token is deleted immediately when execution
  is cancelled. (improvement)
* Ignore lock release errors which could occur while reopening log files. This error could simply
  indicate that the lock was never acquired.


1.2.0 - December 07, 2015
-------------------------

Added
~~~~~

* Add SSH bastion host support to the paramiko SSH runner. Utilizes same connection parameters as
  the targeted box. (new feature, improvement) #2144, #2150 [Logan Attwood]
* Introduce a new ``timeout`` action execution status which represents an action execution
  timeout. Previously, executions which timed out had status set to ``failure``. Keep in mind
  that timeout is just a special type of a failure. (new feature)
* Allow jinja templating to be used in ``message`` and ``data`` field for notifications.(new feature)
* Add tools for purging executions (also, liveactions with it) and trigger instances older than
  certain UTC timestamp from the db in bulk.
* Introducing ``noop`` runner and ``core.noop`` action. Returns consistent success in a WF regardless of
  user input. (new feature)
* Add mock classes (``st2tests.mocks.*``) for easier unit testing of the packs. (new feature)
* Add a script (``./st2common/bin/st2-run-pack-tests``) for running pack tests. (new feature)
* Support for formatting of alias acknowledgement and result messages in AliasExecution. (new feature)
* Support for "representation+value" format strings in aliases. (new feature)
* Support for disabled result and acknowledgement messages in aliases. (new feature)
* Add ability to write rule enforcement (models that represent a rule evaluation that resulted
  in an action execution) to db to help debugging rules easier. Also, CLI bindings to list
  and view these models are added. (new-feature)

Changed
~~~~~~~

* Refactor retries in the Mistral action runner to use exponential backoff. Configuration options
  for Mistral have changed. (improvement)
* Update action chain runner so it performs on-success and on-error task name validation during
  pre_run time. This way common errors such as typos in the task names can be spotted early on
  since there is no need to wait for the run time.
* Change ``headers`` and ``params`` ``core.http`` action paramer type from ``string`` to
  ``object``.
* Don't allow action parameter ``type`` attribute to be an array since rest of the code doesn't
  support parameters with multiple types. (improvement)
* Update local runner so all the commands which are executed as a different user and result in
  using sudo set $HOME variable to the home directory of the target user. (improvement)
* Include state_info for Mistral workflow and tasks in the action execution result. (improvement)
* ``--debug`` flag no longer implies profiling mode. If you want to enable profiling mode, you need
  to explicitly pass ``--profile`` flag to the binary. To reproduce the old behavior, simply pass
  both flags to the binary - ``--debug --profile``.
* Modify ActionAliasFormatParser to work with regular expressions and support more flexible parameter matching. (improvement)
* Move ChatOps pack to st2 core.
* Purge tool now uses delete_by_query and offloads delete to mongo and doesn't perform app side
  explicit model deletion to improve speed. (improvement)

Fixed
~~~~~

* Fix trigger parameters validation for system triggers during rule creation - make sure we
  validate the parameters before creating a TriggerDB object. (bug fix)
* Fix a bug with a user inside the context of the live action which was created using alias
  execution endpoint incorrectly being set to the system user (``stanley``) instead of the
  authenticated user which triggered the execution. (bug fix)
* Fix policy loading and registering - make sure we validate policy parameters against the
  parameters schema when loading / registering policies. (bug fix, improvement)
* Fix policy trigger for action execution cancellation. (bug fix)
* Improve error reporting for static error in ActionChain definition e.g. incorrect reference
  in default etc. (improvement)
* Fix action chain so it doesn't end up in an infinite loop if an action which is part of the chain
  is canceled. (bug fix)
* Fix json representation of trace in cli. (bug fix)
* Add missing indexes on trigger_instance_d_b collection. (bug fix)


1.1.1 - November 13, 2015
-------------------------

Added
~~~~~

* Allow user to specify URL which Mistral uses to talk to StackStorm API using ``mistral.api_url``
  configuration option. If this option is not provided it defaults to the old behavior of using the
  public API url (``auth.api_url`` setting). (improvement)

Changed
~~~~~~~

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

Fixed
~~~~~

* Fix a race condition in sensor container where a sensor which takes <= 5 seconds to shut down
  could be respawned before it exited. (bug fix) #2187 [Kale Blankenship]
* Add missing entry for ``st2notifier`` service to the logrotate config. (bug fix)
* Allow action parameter values with type ``object`` to contain special characters such as
  ``.`` and ``$`` in the parameter value. (bug fix, improvement)


1.1.0 - October 27, 2015
------------------------

Added
~~~~~

* Add YAQL v1.0 support to Mistral. Earlier versions are deprecated. (improvement)
* Move st2auth service authentication backends to a "repo per backend" model. Backends are now also
  dynamically discovered and registered which makes it possible to easily create and use custom
  backends. For backward compatibility reasons, ``flat_file`` backend is installed and available by
  default. (new feature, improvement)
* New st2auth authentication backend for authenticating against LDAP servers -
  https://github.com/StackStorm/st2-auth-backend-ldap. (new feature)
* Enable Mistral workflow cancellation via ``st2 execution cancel``. (improvement)
* Allow action-alias to be created and deleted from CLI.
* Add support for ``--profile`` flag to all the services. When this flag is provided service runs
  in the profiling module which means all the MongoDB queries and query related profile data is
  logged. (new-feature)
* Introduce API Keys that do not expire like Authentication tokens. This makes it easier to work
  with webhook based integrations. (new-feature)
* Allow user to define trigger tags in sensor definition YAML files. (new feature) #2000
  [Tom Deckers]
* Update CLI so it supports caching tokens for different users (it creates a different file for each
  user). This means you can now use ``ST2_CONFIG_FILE`` option without disabling token cache.
  (improvement)
* Add option to verify SSL cert for HTTPS request to the core.http action. (new feature)
* Allow user to update / reinstall Python dependencies listed in ``requirements.txt`` inside the
  pack virtual environment by passing ``update=True`` parameter to ``packs.setup_virtualenv``
  action or by using new ``packs.update_virtualenv`` action. (new feature)
  [jsjeannotte]
* Pack on install are now assigned an owner group. The ``pack_group`` property allows to pick this
  value and default is ``st2packs``. (new feature)

Changed
~~~~~~~

* Update CLI so ``st2 run`` / ``st2 execution run`` and ``st2 execution re-run`` commands exit with
  non-zero code if the action fails. (improvement)
* Default to rule being disabled if the user doesn't explicitly specify ``enabled`` attribute when
  creating a rule via the API or inside the rule metadata file when registering local content
  (previously it defaulted to enabled).
* Include parameters when viewing execution via the CLI. (improvement)
* CLI renders parameters and output as yaml for better readability. (improvement)
* Support versioned APIs for auth controller. For backward compatibility, unversioned API calls
  get redirected to versioned controllers by the server. (improvement)
* Update remote runner to include stdout and stderr which was consumed so far when a timeout
  occurs. (improvement)
* Reduce the wait time between message consumption by TriggerWatcher to avoid latency (improvement)
* Allow user to specify value for the ``From`` field in the ``sendmail`` action by passing ``from``
  parameter to the action. (improvement)
  [pixelrebel]

Deprecated
~~~~~~~~~~

* YAQL versions < 1.0 are deprecated.

Fixed
~~~~~

* Fix ``timestamp_lt`` and ``timestamp_gt`` filtering in the `/executions` API endpoint. Now we
  return a correct result which is expected from a user-perspective. (bug-fix)
* Make sure that alias execution endpoint returns a correct status code and error message if the
  referenced action doesn't exist.
* Allow user to select ``keystone`` backend in the st2auth service. (bug-fix)
* Fix ``packs.info`` action so it correctly exits with a non-zero status code if the pack doesn't
  exist or if it doesn't contain a valid ``.gitinfo`` file. (bug-fix)
* Fix ``packs.info`` action so it correctly searches all the packs base dirs. (bug-fix)
* Fix a bug in ``stdout`` and ``stderr`` consumption in paramiko SSH runner where reading a fixed
  chunk byte array and decoding it could result in multi-byte UTF-8 character being read half way
  resulting in UTF-8 decode error. This happens only when output is greater than default chunk size
  (1024 bytes) and script produces utf-8 output. We now collect all the bytes from channel
  and only then decode the byte stream as utf-8.
* Cleanup timers and webhook trigger definitions once all rules referencing them are removed. (bug-fix)
* Enable pseudo tty when running remote SSH commands with the paramiko SSH runner. This is done
  to match existing Fabric behavior. (bug-fix)
* Fix CLI so it skips automatic authentication if credentials are provided in the config on "auth"
  command. (bug fix)
* Strip the last '\r' or '\r\n' from both ``stdout`` and ``stderr`` streams from paramiko and local
  runner output. This is done to be compatible with fabric output of those streams. (bug-fix)
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
* Fix st2-self-check script to check whether to use http/https when connecting to st2, to disable
  Windows test by default, and to check test status correctly. (bug-fix)
* Use exclusive messaging Qs for TriggerWatcher to avoid having to deal with old messages
  and related migration scripts. (bug-fix)
* Make sure sensor container child processes (sensor instance processes) are killed and cleaned up
  if the sensor container is forcefully terminated (SIGKILL). (bug fix, improvement)


0.13.2 - September 09, 2015
---------------------------

Changed
~~~~~~~

* Last newline character (``\n``) is now stripped from ``stdout`` and ``stderr`` fields in local
  and remote command/shell runners. (improvement)
* Make sure sensor processes correctly pick up parent ``--debug`` flag. This makes debugging a lot
  easier since user simply needs to start sensor container with ``--debug`` flag and all the sensor
  logs with level debug or higher will be routed to the container log. (improvement)

Fixed
~~~~~

* ``private_key`` supplied for remote_actions is now used to auth correctly. The ``private_key``
  argument should be the contents of private key file (of user specified in username argument).
  (bug-fix)
* Fix sensor container service so the ``config`` argument is correctly passed to the sensor
  instances in the system packs. Previously, this argument didn't get passed correctly to the
  FileWatchSensor from the system linux pack. (bug-fix)


0.13.1 - August 28, 2015
------------------------

Fixed
~~~~~

* ``cwd`` for paramiko script runner should use ``cwd`` provided as runner parameter.
  (bug-fix)
* Fix timer regression; bring brack broken timers. (bug-fix)
* Updates to trace objects are done via non-upsert updates by adding to the array. This
  makes it safer to update trace objects from multiple processes. (bug-fix)


0.13.0 - August 24, 2015
------------------------

Added
~~~~~

* Add new OpenStack Keystone authentication backend.
  [Itxaka Serrano]
* Support for RabbitMQ cluster. StackStorm works with a RabbitMQ cluster and switches
  nodes on failover. (feature)
* Introduce a Paramiko SSH runner that uses eventlets to run scripts or commands in parallel.
  (improvement) (experimental)
* Add action parameters validation to Mistral workflow on invocation. (improvement)
* Allow user to include files which are written on disk inside the action create API payload.
  (new feature)
* Allow user to retrieve content of a file inside a pack by using the new
  ``/packs/views/files/`` API endpoint. (new feature)
* Add OpenStack Keystone authentication configuration for Mistral. (improvement)
* Ability to add trace tag to TriggerInstance from Sensor. (feature)
* Ability to view trace in CLI with list and get commands. (feature)
* Add ability to add trace tag to ``st2 run`` CLI command. (feature)
* Add ability to specify trace id in ``st2 run`` CLI command. (feature)
* Add ``X-Request-ID`` header to all API calls for easier debugging. (improvement)
* Add new CLI commands for disabling and enabling content pack resources
  (``{sensor,action,rule} {enable, disable} <ref or id>``) (feature)

Changed
~~~~~~~

* Information about parent workflow is now a dict in child's context field. (improvement)
* Add support for restarting sensors which exit with a non-zero status code to
  the sensor container. Sensor container will now automatically try to restart
  (up to 2 times) sensor processes which die with a non-zero status code. (improvement)
* Add index to the ActionExecution model to speed up query. (improvement)
* Rename notification "channels" to "routes". (improvement)
* Turn on paramiko ssh runner as the default ssh runner in prod configuration.
  To switch to fabric runner, set ``use_paramiko_ssh_runner`` to false in ``st2.conf``.
  (improvement)

Fixed
~~~~~

* Fix a bug when some runner parameter default values were not overridden when a
  false value was used in the action metadata parameter override (e.g. False, 0).
  [Eugen C.]
* Correctly return 404 if user requests an invalid path which partially maps to an existing
  path. (bug-fix)
* Fix sort key in the ActionExecution API controller. (bug-fix)
* Fix key name for error message in liveaction result. (bug-fix)
* Fix 500 API response when rule with no pack info is supplied. (bug-fix)
* Fix bug in trigger-instance re-emit (extra kwargs passed to manager is now handled). (bug-fix)
* Make sure auth hook and middleware returns JSON and "Content-Type: application/json" header
  in every response. (improvement, bug-fix)
* Fix bug in triggers emitted on key value pair changes and sensor spawn/exit. When
  dispatching those triggers, the reference used didn't contain the pack names
  which meant it was invalid and lookups in the rules engine would fail. (bug-fix)
* Handle ``sudo`` in paramiko remote script runner. (bug-fix)
* Update ``st2ctl`` to correctly start ``st2web`` even if Mistral is not installed.
  (bug-fix, improvement)
* Fix a bug in handling positional arguments with spaces. (bug-fix)
* Make sure that the ``$PATH`` environment variable which is set for the sandboxed Python
  process contains ``<virtualenv path>/bin`` directory as the first entry. (bug fix)


0.12.2 - August 11, 2015
------------------------

Added
~~~~~

* Support local ssh config file in remote runners. (feature)

Changed
~~~~~~~

* Changes to htpasswd file used in ``flat_file`` auth backend do not require
  a restart of st2auth and consequently StackStorm. (feature)


0.12.1 - July 31, 2015
----------------------

Fixed
~~~~~

* Un-registering a pack also removes ``rules`` and ``action aliases`` from the pack. (bug-fix)
* Disable parallel SSH in fabric runner which causes issues with eventlets. (bug-fix)
* Fix executions stuck in ``running`` state if runner container throws exception. (bug-fix)
* Fix cases where liveaction result in dict are escaped and passed to Mistral. (bug-fix)


0.12.0 - July 20, 2015
----------------------

Added
~~~~~

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
* Allow user to specify new ``secret`` attribute (boolean) for each action parameters. Values of
  parameters which have this attribute set to true will be masked in the log files. (new-feature)
* Support for masking secret parameters in the API responses. Secret parameters can only be viewed
  through the API by admin users. (new-feature)
* ``six`` library is now available by default in the Python sandbox to all the newly installed
  packs. (improvement)
* Dispatch an internal trigger when a datastore item has been created, updated, deleted and when
  it's value has changed. (new-feature)
* Add new ``/v1/packs`` API endpoint for listing installed packs. (new-feature)
* Ability to partition sensors across sensor nodes using various partition schemes. (new-feature)
* Add ability to use action context params as action params in meta. (new-feature)

Changed
~~~~~~~

* Allow users to use ``timediff_lt`` and ``timediff_gt`` rule comparison operator with many string
  date formats - previously it only worked with ISO8601 date strings. (improvement)
* API server now gracefully shuts down on SIGINT (CTRL-C). (improvement)
* Single sensor mode of Sensor Container uses ``--sensor-ref`` instead of ``--sensor-name``.
* Move ``/exp/actionalias/`` and ``/exp/aliasexecution`` to ``/v1/actionalias/`` and
  ``/v1/aliasexecution/`` respectively. (upgrade)
* Display friendly message for error in parameters validation on action execution. (improvement)

Fixed
~~~~~

* Fix a bug with with reinstalling a pack with no existing config - only try to move the config
  file over if it exists. (bug fix)
* Fix a bug with ``st2 execution list`` CLI command throwing an exception on failed Mistral
  workflows. (bug-fix)
* Fix a bug with ``st2 execution list`` CLI command not displaying ``end_timestamp`` attribute for
  Mistral workflows. (bug-fix)
* Fix a bug in action container where rendering params was done twice. (bug-fix)


0.11.6 - July 2, 2015
---------------------

Changed
~~~~~~~

* Update all the code to handle all the datetime objects internally in UTC. (improvement, bug-fix)


0.11.5 - July 1, 2015
---------------------

Fixed
~~~~~

* Fix a bug where ``end_timestamp`` is not captured for Mistral workflow executions (bug-fix)
* Fix a bug where the CLI failed to display Mistral workflow that errored (bug-fix)
* Fix a bug where the published variables are not captured in the Mistral workflow result (bug-fix)


0.11.4 - June 30, 2015
----------------------

Removed
~~~~~~~

* Remove unnecessary rule notify_hubot from core.


0.11.3 - June 16, 2015
----------------------

Fixed
~~~~~

* Fix RHEL6 packaging issues


0.11.2 - June 12, 2015
----------------------

Fixed
~~~~~

* Fix a bug with ``start_timestamp`` and ``end_timestamp`` sometimes returning an invalid value in
  a local instead of UTC timezone. (bug-fix)
* Fix to get PollingSensor working again. Sensors of type PollingSensor were not being treated
  as such and as a result would fail after the 1st poll. (bug-fix)


0.11.1 - June 8, 2015
---------------------

Changed
~~~~~~~

* Action aliases are registered by default. (improvement)

Fixed
~~~~~

* Repair failing pack installation. (bug-fix)


0.11.0 - June 5, 2015
---------------------

Added
~~~~~

* Allow user to configure the CLI using an ini style config file located at ``~/.st2rc``.
  (new-feature)
* Add support for caching of the retrieved auth tokens to the CLI. (new-feature)
* Update CLI so it displays the error at the top level when using ``run``, ``execution run`` or
  ``execution get`` when executed workflow fails. (improvement)
* Add new API endpoint for re-running an execution (``POST /executions/<id>/re_run/``).
  (new-feature)
* CLI now has ``get`` and ``list`` commands for triggerinstance. (new-feature)
* CLI now has ``re-emit`` command for triggerinstance. (new-feature)

Changed
~~~~~~~

* Throw a more-user friendly exception when enforcing a rule if an action referenced inside
  the rule definition doesn't exist. (improvement)
* Rules should be part of a pack. (improvement)
* Update Windows runner code so it also works with a newer versions of winexe (> 1.0).
  (improvement) [James Sigurðarson]
* Validate parameters during rule creation for system triggers. (improvement)

Fixed
~~~~~

* Fix a bug with the rule evaluation failing if the trigger payload contained a key with a
  dot in the name. (bug-fix)
* Fix a bug with publishing array (list) values as strings inside the action chain workflows.
  (bug-fix)
* Action trigger now contains execution id as opposed to liveaction id. (bug-fix)

v0.9.2 - May 26, 2015
---------------------

Fixed
~~~~~

* Fix broken ``packs.download`` action. (bug-fix)


v0.9.1 - May 12, 2015
---------------------

Added
~~~~~

* Allow option to bypass SSL Certificate Check (improvement)

Changed
~~~~~~~

* Return HTTP BAD REQUEST when TTL requested for token > Max configured TTL (improvement)

Fixed
~~~~~

* Fix a bug with alias parser to support empty formats (bug-fix)


v0.9.0 - April 29, 2015
-----------------------

Added
~~~~~

* Sensor container now can dynamically load/reload/unload sensors on data model changes.
  (new-feature)
* Add ``-t`` / ``--only-token`` flag to the ``st2 auth`` command. (new-feature)
* Add ability to best-effort cancel actions and actionchain via API. (new-feature)
* Add new ``windows-cmd`` and ``windows-script`` runners for executing commands
  and PowerShell scripts on Windows hosts. (new-feature)
* Update all the Python services to re-open log files on the ``SIGUSR1`` signal. (new-feature)

Changed
~~~~~~~

* Report a more user-friendly error if an action-chain task references an invalid or inexistent
  action. Also treat invalid / inexistent action as a top-level action-chain error. (improvement)
* Report a more user-friendly error if an action-chain definition contains an invalid type.
  (improvement)
* Rename all st2 processes to be prefixed by st2. (sensor_container is now st2sensorcontainer,
  rules_engine is now st2rulesengine, actionrunner is now st2actionrunner) (improvement)
* Return a user friendly error on no sensors found or typo in sensor class name in single
  sensor mode. (improvement)
* Check if internal trigger types are already registered before registering
  them again. (improvement)
* Update runner names so they follow a consistent naming pattern. For backward
  compatibility reasons, runners can still be referenced using their old names.
  (improvement)

Fixed
~~~~~

* Sensor container now returns non-zero exit codes for errors. (bug-fix)
* Fix a bug in datastore operations exposed in st2client. (bug-fix)
* Catch exception if rule operator functions throw excepton and ignore the rule. (bug-fix)
* Remove expected "runnertype not found" error logs on action registration
  in clean db. (improvement)
* Clean up rule registrar logging. (improvement)
* ``register`` param in packs.install should be passed to packs.load. (bug-fix)
* Fix validation code to validate value types correctly. (bug-fix)
* Internal trigger types registered using APIs should use auth token. (bug-fix)

Security
~~~~~~~~

* Enable authentication by default for package based installations.


v0.8.3 - March 23, 2015
-----------------------

Changed
~~~~~~~

* Don't allow ``run-remote-script`` actions without an ``entry_point`` attribute - throw an
  exception when running an action. (improvement)

Fixed
~~~~~

* Fix ``packs.setup_virtualenv`` command so it works correctly if user has specified multiple packs
  search paths. (bug-fix)
* Update sensor container to use ``auth.api_url`` setting when talking to the API (e.g. when
  accessing a datastore, etc.). This way it also works correctly if sensor container is running
  on a different host than the API. (bug-fix)

v0.8.2 - March 10, 2015
-----------------------

Fixed
~~~~~

* Fix a bug with python-runner actions sometimes not correctly reporting the action's ``stdout``.
  (bug-fix)
* Fix a bug in the ``run-remote-script`` runner - the runner ignored environment variables and
  authentication settings which were supplied to the action as parameters. (bug-fix)


v0.8.1 - March 10, 2015
-----------------------

Added
~~~~~

* Allow user to exclude particular attributes from a response by passing
  ``?exclude_attributes=result,trigger_instance`` query parameter to the ``/actionexecutions/``
  and ``/actionexecutions/<execution id>/`` endpoint (new-feature)
* Add new ``/actionexecutions/<id>/attribute/<attribute name>`` endpoint which allows user to
  retrieve a value of a particular action execution attribute. (new-feature)

Changed
~~~~~~~

* Update ``execution get`` CLI command so it automatically detects workflows and returns more
  user-friendly output by default. (improvement)
* Update ``run``, ``action execute``, ``execution get`` and ``execution re-run`` CLI commands to
  take the same options and return output in the same consistent format.
* Throw a more friendly error in the action chain runner if it fails to parse the action chain
  definition file. (improvement)

Fixed
~~~~~

* Fix a bug with http runner not parsing JSON HTTP response body if the content-type header also
  contained a charset. (bug-fix)
* Indent workflow children properly in CLI (bug-fix)
* Make sure that wait indicator is visible in CLI on some systems where stdout is buffered. (bug-fix)
* Fix a bug with ``end_timestamp`` attribute on the ``LiveAction`` and ``ActionExecution`` model
  containing an invalid value if the action hasn't finished yet. (bug-fix)
* Correctly report an invalid authentication information error in the remote runner. (bug-fix)
* Fix a bug in the action chain runner and make sure action parameters are also available for
  substitution in the ``publish`` scope. (bug-fix)


v0.8.0 - March 2, 2015
----------------------

Added
~~~~~

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
* Vars can be defined in the ActionChain. (new-feature)
* Node in an ActionChain can publish global variables. (new-feature)
* Allow user to provide authentication token either inside headers (``X-Auth-Token``) or via
  ``x-auth-token`` query string parameter. (new-feature)
* Allow user to override authentication information (username, password, private key) on per
  action basis for all the remote runner actions. (new-feature)
* Allow user to pass ``--inherit-env`` flag to the ``st2 action run`` command which causes all
  the environment variables accessible to the CLI to be sent as ``env`` parameter to the action
  being executed. (new-feature)
* Cast params of an execution before scheduling in the RulesEngine. This allows non-string
  parameters in an action. (new-feature)
* CLI commands to return non-zero exit codes for failed operations (new-feature)
* Add new ``nequals`` (``neq``) rule criteria operator. This criteria operator
  performs not equals check on values of an arbitrary type. (new-feature)
* Add new ``execution re-run <execution id>`` CLI command for re-running an
  existing action. (new-feature)
* Dispatch an internal trigger when a sensor process is spawned / started
  (``st2.sensor.process_spawn``) and when a process exits / is stopped
  (``st2.sensor.process_exit``). (new-feature)
* Update HTTP runner to automatically parse JSON response body if Content-Type is
  ``application/json`` (new-feature)
* Support for filtering by timestamp and status in executions list. (new-feature)
* Ability to see child tasks of any execution. (new-feature)
* Allow sensors to manage global datastore items via sensor_service by passing ``local=False``
  argument to the ``get_value``, ``set_value`` and ``delete_value`` methods. (new-feature)
* Allow sensors to list datastore items using ``list_values`` sensor_service method. (new-feature)
* Allow users to filter datastore items by name prefix by passing ``?prefix=<value>`` query
  parameter to the ``/keys`` endpoint. (new-feature)

Changed
~~~~~~~

* Rename ActionExecution to LiveAction. (refactor)
* Rename ActionExecutionHistory to ActionExecution. (refactor)
* POST to ``/v1/executions`` take LiveActionAPI but returns ActionExecutionAPI (refactor)
* Execution list shows only top level executions by default to see full list use --showall. (refactor)

Removed
~~~~~~~

* A separate history process is no longer required. ActionExecution updates are carried at time of
  update to LiveAction. (refactor)

Deprecated
~~~~~~~~~~

* API url ``/v1/actionexecutions/`` is now deprecated in favor of ``/v1/executions/`` (refactor)
* API url change ``/v1/history/execution`` to ``/v1/executions`` (refactor)
* API url change ``/v1/history/execution/views/filters`` to ``/v1/executions/views/filters`` (refactor)

Fixed
~~~~~

* Fix a race-condition / bug which would occur when multiple packs are installed at the same time.
  (bug-fix)
* Allow actions without parameters. (bug-fix)
* Fix a bug with rule matching not working for any triggers with parameters. (bug-fix)
* Require ``cmd`` parameter for the following actions: ``core.remote``, ``core.remote_sudo``,
  ``core.local``, ``core.local_sudo`` (bug-fix)
* Use QuerySet.count() instead of len(QuerySet) to avoid the caching of the entire result which
  improve running time of API request. (bug-fix)
* Fix a bug with template rendering, under some conditions, ending in an infinite loop. (bug-fix)
* Mistral subworkflows kicked off in st2 should include task name. (bug-fix)
* Fix non-string types to be rendered correctly in action parameters when used in rule. (bug-fix)
* Allow user to specify default value for required attributes in the definition of action
  parameters. (bug-fix)
* When running with auth enabled, correctly preserve the username of the authenticated user who
  has triggered the action execution. (bug-fix)


v0.7 - January 16, 2015
-----------------------

Added
~~~~~

* Python runner and all the fabric based runners (``run-local``, ``run-local-script``,
  ``run-remote``, ``run-remote-script``) now expose the ``timeout`` argument. With this argument
  users can specify action timeout. Previously, the action timeout was not user-configurable and
  a system-wide default value was used.
* The time when an action execution has finished is now recorded and available via the
  ``end_timestamp`` attribute on the ``ActionExecution`` model.
* Allow polling sensors to retrieve current poll interval and change it using ``get_poll_interval``
  and ``set_poll_interval`` methods respectively. (new-feature)
* Add support for a ``standalone`` mode to the st2auth service. In the standalone mode,
  authentication is handled inside the st2auth service using the defined backend. (new feature)
* Add new rule criteria comparison operators: ``iequals``, ``contains``, ``icontains``,
  ``ncontains``, ``incontains``, ``startswith``, ``istartswith``, ``endswith``, ``iendswith``,
  ``exists``, ``nexists`` (new-feature)
* Allow sensors to store temporary data in the datastore using the ``get_value``, ``set_value`` and
  ``delete_value`` methods exposed by sensor_service. (new-feature)
* Allow user to specify TTL for datastore values by sending ``ttl`` attribute in the body of a
  ``PUT /keys/<key id>`` request. (new feature)
* Add new ``key delete_by_prefix --prefix=<prefix>`` client command. This command allows deletion of
  all the keys with names starting with the provided prefix. (new-feature)
* Add ability to attach tags to Action, Rule and TriggerType.
* Add ability to query results asynchronously from external services. (new-feature)
* Add ``rule_tester`` tool which allows users to test rules in an offline mode without any services
  running (new-feature)

Changed
~~~~~~~

* Refactor local runners so they are more robust, efficient and easier to debug. Previously, local
  actions were executed through SSH, now they are executed directly without the overhead of SSH.
* Timer is not a sensor anymore. It is launched as part of the ``rules_engine`` process (refactor)
* Action models now use ContentPackResourceMixin so we can get them by ref. (refactor)
* st2api only requires st2common and dependencies defined in ``requirements.txt`` to be available
  on the pythonpath thus making it possible to run st2api standalone.
* Change default mode for authentication to standalone. (refactor)

Fixed
~~~~~

* Status code 400 (bad request) is now returned if user doesn't provide a body to API endpoints
  which require it. Previously 500 internal server error was returned (bug-fix).
* Fix local runner so it correctly executes a command under the provided system user if ``user``
  parameter is provided. (bug-fix)
* Fix a bug with a Trigger database object in some cases being created twice when registering a
  rule. (bug-fix)
* Fix a bug with child processes which run sensor code not being killed when stopping a sensor
  container service. (bug-fix)
* Fix a bug and allow user to use non-ascii (unicode) values in the parameter substitution values.
  (bug-fix)
* Fix a bug with action registration where actions with invalid schema for parameters get
  registered. (bug-fix)
* Fix a bug with ``default`` param values inheritance in runner/actions. (bug-fix)
* Fix a bug where trigger objects weren't created for triggers with different parameters. (bug-fix)


v0.6.0 - December 8, 2014
-------------------------

Added
~~~~~

* Add Sensor and PollingSensor base classes. (NB: Sensors API change is non-backward compatible.)
* YAML support for action, rules and chain meta.
* Add sensor meta support (JSON/YAML) to specify trigger types.
* Audit log messages are now saved in a structured format as JSON in
  ``st2actionrunner.{pid}.audit.log`` log file.

Changed
~~~~~~~

* Separate virtualenv per pack. (Pythonic sensors and actions use them by default.)
* Install pip requirements from ``requirements.txt`` in packs by default.
* Sensors are now run in their own process for isolation.
* Python Actions are now run in their own process for isolation.
* Separate out ``rules_engine`` into own process.
* Packs default path moves from ``/opt/stackstorm`` to ``/opt/stackstorm/packs/``.
* Webhooks are not part of a sensor. They are now part of core API. (Authentication may
  be required.)
* API URLs are now versioned. All the existing paths have been prefixed with ``/v1``
  (e.g. ``/v1/actions``).

Fixed
~~~~~

* Numerous bug fixes.

v0.5.1 - November 3rd, 2014
---------------------------

Added
~~~~~

* Initial public release
