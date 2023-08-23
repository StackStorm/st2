Changelog
=========

in development
--------------

Fixed
~~~~~

* Fix CI usses #6015
  Contributed by Amanda McGuinness (@amanda11 intive)

Added
~~~~~
* Move `git clone` to `user_home/.st2packs` #5845

* Error on `st2ctl status` when running in Kubernetes. #5851
  Contributed by @mamercad

* Continue introducing `pants <https://www.pantsbuild.org/docs>`_ to improve DX (Developer Experience)
  working on StackStorm, improve our security posture, and improve CI reliability thanks in part
  to pants' use of PEX lockfiles. This is not a user-facing addition.
  #5778 #5789 #5817 #5795 #5830 #5833 #5834 #5841 #5840 #5838 #5842 #5837 #5849 #5850
  #5846 #5853 #5848 #5847 #5858 #5857 #5860 #5868 #5871 #5864 #5874 #5884 #5893 #5891
  #5890 #5898 #5901 #5906 #5899 #5907 #5909 #5922 #5926 #5927 #5925 #5928 #5929 #5930
  #5931 #5932 #5948 #5949 #5950
  Contributed by @cognifloyd

* Added a joint index to solve the problem of slow mongo queries for scheduled executions. #5805

* Added publisher to ActionAlias to enable streaming ActionAlias create/update/delete events. #5763
  Contributed by @ubaumann

* Expose environment variable ST2_ACTION_DEBUG to all StackStorm actions.
  Contributed by @maxfactor1

* Added option to checkout git submodules when downloading/installing packs #5814
  Contributed by @jk464

3.8.0 - November 18, 2022
-------------------------

Fixed
~~~~~

* Fix redis SSL problems with sentinel #5660

* Fix a bug in the pack config loader so that objects covered by an ``patternProperties`` schema
  or arrays using ``additionalItems`` schema(s) can use encrypted datastore keys and have their
  default values applied correctly. #5321

  Contributed by @cognifloyd

* Fixed ``st2client/st2client/base.py`` file to check for http_proxy and https_proxy environment variables for both lower and upper cases.

  Contributed by @S-T-A-R-L-O-R-D

* Fixed a bug where calling 'get_by_name' on client for getting key details was not returning any results despite key being stored. #5677

  Contributed by @bharath-orchestral

* Fixed ``st2client/st2client/base.py`` file to use ``https_proxy``(not ``http_proxy``) to check HTTPS_PROXY environment variables.

  Contributed by @wfgydbu

* Fixed schema utils to more reliably handle schemas that define nested arrays (object-array-object-array-string) as discovered in some
  of the ansible installer RBAC tests (see #5684). This includes a test that reproduced the error so we don't hit this again. #5685

* Fixed eventlet monkey patching so more of the unit tests work under pytest. #5689

* Fix and reenable prance-based openapi spec validation, but make our custom ``x-api-model`` validation optional as the spec is out-of-date. #5709
  Contributed by @cognifloyd

* Fixed generation of `st2.conf.sample` to show correct syntax for `[sensorcontainer].partition_provider` (space separated `key:value` pairs). #5710
  Contributed by @cognifloyd

* Fix access to key-value pairs in workflow and action execution where RBAC rules did not get applied #5764

  Contributed by @m4dcoder

* Add backward compatibility to secret masking introduced in #5319 to prevent security-relative issues.
  Migration to the new schema is required to take advantage of the full output schema validation. #5783

  Contributed by @m4dcoder


Added
~~~~~

* Added graceful shutdown for workflow engine. #5463
  Contributed by @khushboobhatia01

* Add ``ST2_USE_DEBUGGER`` env var as alternative to the ``--use-debugger`` cli flag. #5675
  Contributed by @cognifloyd

* Added purging of old tokens. #5679
  Contributed by Amanda McGuinness (@amanda11 intive)

* Begin introducing `pants <https://www.pantsbuild.org/docs>`_ to improve DX (Developer Experience)
  working on StackStorm, improve our security posture, and improve CI reliability thanks in part
  to pants' use of PEX lockfiles. This is not a user-facing addition. #5713 #5724 #5726 #5725 #5732 #5733 #5737 #5738 #5758 #5751 #5774 #5776 #5777 #5782
  Contributed by @cognifloyd

* Added querytype parameter to linux.dig action to allow specifying the dig 'type' parameter. Fixes #5772

  Contributed by @AmbiguousYeoman

Changed
~~~~~~~

* BREAKING CHANGE for anyone that uses ``output_schema``, which is disabled by default.
  If you have ``[system].validate_output_schema = True`` in st2.conf AND you have added
  ``output_schema`` to any of your packs, then you must update your action metadata.

  ``output_schema`` must be a full jsonschema now. If a schema is not well-formed, we ignore it.
  Now, ``output`` can be types other than object such as list, bool, int, etc.
  This also means that all of an action's output can be masked as a secret.

  To get the same behavior, you'll need to update your output schema.
  For example, this schema:

  .. code-block:: yaml

    output_schema:
      property1:
        type: bool
      property2:
        type: str

  should be updated like this:

  .. code-block:: yaml

    output_schema:
      type: object
      properties:
        property1:
          type: bool
        property2:
          type: str
      additionalProperties: false

  #5319

  Contributed by @cognifloyd

* Changed the `X-XSS-Protection` HTTP header from `1; mode=block` to `0` in the `conf/nginx/st2.conf` to align with the OWASP security standards. #5298

  Contributed by @LiamRiddell

* Use PEP 440 direct reference requirements instead of legacy PIP VCS requirements. Now, our ``*.requirements.txt`` files use
  ``package-name@ git+https://url@version ; markers`` instead of ``git+https://url@version#egg=package-name ; markers``. #5673
  Contributed by @cognifloyd

* Move from udatetime to ciso8601 for date functionality ahead of supporting python3.9 #5692
  Contributed by Amanda McGuinness (@amanda11 intive)

* Refactor tests to use python imports to identify test fixtures. #5699 #5702 #5703 #5704 #5705 #5706
  Contributed by @cognifloyd

* Refactor ``st2-generate-schemas`` so that logic is in an importable module. #5708
  Contributed by @cognifloyd

Removed
~~~~~~~

* Removed st2exporter service. It is unmaintained and does not get installed. It was
  originally meant to help with analytics by exporting executions as json files that
  could be imported into something like elasticsearch. Our code is now instrumented
  to make a wider variety of stats available to metrics drivers. #5676
  Contributed by @cognifloyd

3.7.0 - May 05, 2022
--------------------

Added
~~~~~

* Added st2 API get action parameters by ref. #5509

  API endpoint ``/api/v1/actions/views/parameters/{action_id}`` accepts ``ref_or_id``.

  Contributed by @DavidMeu

* Enable setting ttl for MockDatastoreService. #5468

  Contributed by @ytjohn

* Added st2 API and CLI command for actions clone operation.

  API endpoint ``/api/v1/actions/{ref_or_id}/clone`` takes ``ref_or_id`` of source action.
  Request method body takes destination pack and action name. Request method body also takes
  optional parameter ``overwrite``. ``overwrite = true`` in case of destination action already exists and to be
  overwritten.

  CLI command ``st2 action clone <ref_or_id> <dest_pack> <dest_action>`` takes source ``ref_or_id``, destination
  pack name and destination action name as mandatory arguments.
  In case destination already exists then command takes optional argument ``-f`` or ``--force`` to overwrite
  destination action. #5345

  Contributed by @mahesh-orch.

* Implemented RBAC functionality for existing ``KEY_VALUE_VIEW, KEY_VALUE_SET, KEY_VALUE_DELETE`` and new permission types ``KEY_VALUE_LIST, KEY_VALUE_ALL``.
  RBAC is enabled in the ``st2.conf`` file. Access to a key value pair is checked in the KeyValuePair API controller. #5354

  Contributed by @m4dcoder and @ashwini-orchestral

* Added service deregistration on shutdown of a service. #5396

  Contributed by @khushboobhatia01

* Added pysocks python package for SOCKS proxy support. #5460

  Contributed by @kingsleyadam

* Added support for multiple LDAP hosts to st2-auth-ldap. #5535, https://github.com/StackStorm/st2-auth-ldap/pull/100

  Contributed by @ktyogurt

* Implemented graceful shutdown for action runner. Enabled ``graceful_shutdown`` in ``st2.conf`` file. #5428

  Contributed by @khushboobhatia01

* Enhanced 'search' operator to allow complex criteria matching on payload items. #5482

  Contributed by @erceth

* Added cancel/pause/resume requester information to execution context. #5554

  Contributed by @khushboobhatia01

* Added `trigger.headers_lower` to webhook trigger payload. This allows rules to match webhook triggers
  without dealing with the case-sensitive nature of `trigger.headers`, as `triggers.headers_lower` providers
  the same headers, but with the header name lower cased. #5038

  Contributed by @Rand01ph

* Added support to override enabled parameter of resources. #5506

  Contributed by Amanda McGuinness (@amanda11 Intive)

* Add new ``api.auth_cookie_secure`` and ``api.auth_cookie_same_site`` config options which
  specify values which are set for ``secure`` and ``SameSite`` attribute for the auth cookie
  we set when authenticating via token / api key in query parameter value (e.g. via st2web).

  For security reasons, ``api.auth_cookie_secure`` defaults to ``True``. This should only be
  changed to ``False`` if you have a valid reason to not run StackStorm behind HTTPs proxy.

  Default value for ``api.auth_cookie_same_site`` is ``lax``. If you want to disable this
  functionality so it behaves the same as in the previous releases, you can set that option
  to ``None``.

  #5248

  Contributed by @Kami.

* Add new ``st2 action-alias test <message string>`` CLI command which allows users to easily
  test action alias matching and result formatting.

  This command will first try to find a matching alias (same as ``st2 action-alias match``
  command) and if a match is found, trigger an execution (same as ``st2 action-alias execute``
  command) and format the execution result.

  This means it uses exactly the same flow as commands on chat, but the interaction avoids
  chat and hubot which should make testing and developing aliases easier and faster. #5143

  #5143

  Contributed by @Kami.

* Add new ``credentials.basic_auth = username:password`` CLI configuration option.

  This argument allows client to use additional set of basic auth credentials when talking to the
  StackStorm API endpoints (api, auth, stream) - that is, in addition to the token / api key
  native StackStorm auth.

  This allows for simple basic auth based multi factor authentication implementation for
  installations which don't utilize SSO.

  #5152

  Contributed by @Kami.

* Add new audit message when a user has decrypted a key whether manually in the container (st2 key get [] --decrypt)
  or through a workflow with a defined config. #5594
  Contributed by @dmork123

* Added garbage collection for rule_enforcement and trace models #5596/5602
  Contributed by Amanda McGuinness (@amanda11 intive)


* Added garbage collection for workflow execution and task execution objects #4924
  Contributed by @srimandaleeka01 and @amanda11

Changed
~~~~~~~

* Minor updates for RockyLinux. #5552

  Contributed by Amanda McGuinness (@amanda11 intive)

* Bump black to v22.3.0 - This is  used internally to reformat our python code. #5606

* Updated paramiko version to 2.10.3 to add support for more key verification algorithms. #5600

Fixed
~~~~~

* Fix deserialization bug in st2 API for url encoded payloads. #5536

  Contributed by @sravs-dev

* Fix issue of WinRM parameter passing fails for larger scripts.#5538

  Contributed by @ashwini-orchestral

* Fix Type error for ``time_diff`` critera comparison. convert the timediff value as float to match
  ``timedelta.total_seconds()`` return. #5462

  Contributed by @blackstrip

* Fix issue with pack option not working when running policy list cli #5534

  Contributed by @momokuri-3

* Fix exception thrown if action parameter contains {{ or {% and no closing jinja characters. #5556

  contributed by @guzzijones12

* Link shutdown routine and sigterm handler to main thread #5555

  Contributed by @khushboobhatia01

* Change compound index for ActionExecutionDB to improve query performance #5568

  Contributed by @khushboobhatia01

* Fix build issue due to MarkUpSafe 2.1.0 removing soft_unicode

  Contributed by Amanda McGuinness (@amanda11 intive) #5581

* Fixed regression caused by #5358. Use string lock name instead of object ID. #5484

  Contributed by @khushboobhatia01

* Fix ``st2-self-check`` script reporting falsey success when the nested workflows runs failed. #5487

* Fix actions from the contrib/linux pack that fail on CentOS-8 but work on other operating systems and distributions. (bug fix) #4999 #5004

  Reported by @blag and @dove-young contributed by @winem.

* Use byte type lock name which is supported by all tooz drivers. #5529

  Contributed by @khushboobhatia01

* Fixed issue where pack index searches are ignoring no_proxy #5497

  Contributed by @minsis

* Fixed trigger references emitted by ``linux.file_watch.line``. #5467

  Prior to this patch multiple files could be watched but the rule reference of last registered file
  would be used for all trigger emissions causing rule enforcement to fail.  References are now tracked
  on a per file basis and used in trigger emissions.

  Contributed by @nzlosh

* Downgrade tenacity as tooz dependency on tenacity has always been < 7.0.0 #5607

  Contributed by @khushboobhatia01

* Pin ``typing-extensions<4.2`` (used indirectly by st2client) to maintain python 3.6 support. #5638


3.6.0 - October 29, 2021
------------------------

Added
~~~~~

* Added possibility to add new values to the KV store via CLI without leaking them to the shell history. #5164

* ``st2.conf`` is now the only place to configure ports for ``st2api``, ``st2auth``, and ``st2stream``.

  We replaced the static ``.socket`` sytemd units in deb and rpm packages with a python-based generator for the
  ``st2api``, ``st2auth``, and ``st2stream`` services. The generators will get ``<ip>:<port>`` from ``st2.conf``
  to create the ``.socket`` files dynamically. #5286 and st2-packages#706

  Contributed by @nzlosh

Changed
~~~~~~~

* Modified action delete API to delete action files from disk along with backward compatibility.

  From CLI ``st2 action delete <pack>.<action>`` will delete only action database entry.
  From CLI ``st2 action delete --remove-files <pack>.<action>`` or ``st2 action delete -r <pack>.<action>``
  will delete action database entry along with files from disk.

  API action DELETE method with ``{"remove_files": true}`` argument in json body will remove database
  entry of action along with files from disk.
  API action DELETE method with ``{"remove_files": false}`` or no additional argument in json body will remove
  only action database entry. #5304, #5351, #5360

  Contributed by @mahesh-orch.

* Removed --python3 deprecated flag from st2client. #5305

  Contributed by Amanda McGuinness (@amanda11 Ammeon Solutions)

  Contributed by @blag.
* Fixed ``__init__.py`` files to use double quotes to better align with black linting #5299

  Contributed by @blag.

* Reduced minimum TTL on garbage collection for action executions and trigger instances from 7 days to 1 day. #5287

  Contributed by @ericreeves.

* update db connect mongo connection test - `isMaster` MongoDB command depreciated, switch to `ping` #5302, #5341

  Contributed by @lukepatrick

* Actionrunner worker shutdown should stop Kombu consumer thread. #5338

  Contributed by @khushboobhatia01

* Move to using Jinja sandboxed environment #5359

  Contributed by Amanda McGuinness (@amanda11 Ammeon Solutions)

* Pinned python module `networkx` to versions between 2.5.1(included) and 2.6(excluded) because Python v3.6 support was dropped in v2.6.
  Also pinned `decorator==4.4.2` (dependency of `networkx<2.6`) to work around missing python 3.8 classifiers on `decorator`'s wheel. #5376

  Contributed by @nzlosh

* Add new ``--enable-profiler`` flag to all the servies. This flag enables cProfiler based profiler
  for the service in question and  dumps the profiling data to a file on process
  exit.

  This functionality should never be used in production, but only in development environments or
  similar when profiling code. #5199

  Contributed by @Kami.

* Add new ``--enable-eventlet-blocking-detection`` flag to all the servies. This flag enables
  eventlet long operation / blocked main loop logic which throws an exception if a particular
  code blocks longer than a specific duration in seconds.

  This functionality should never be used in production, but only in development environments or
  similar when debugging code. #5199

* Silence pylint about dev/debugging utility (tools/direct_queue_publisher.py) that uses pika because kombu
  doesn't support what it does. If anyone uses that utility, they have to install pika manually. #5380

* Fixed version of cffi as changes in 1.15.0 meant that it attempted to load libffi.so.8. #5390

  Contributed by @amanda11, Ammeon Solutions

* Updated Bash installer to install latest RabbitMQ version rather than out-dated version available
  in OS distributions.

  Contributed by @amanda11, Ammeon Solutions

Fixed
~~~~~

* Correct error reported when encrypted key value is reported, and another key value parameter that requires conversion is present. #5328
  Contributed by @amanda11, Ammeon Solutions

* Make ``update_executions()`` atomic by protecting the update with a coordination lock. Actions, like workflows, may have multiple
  concurrent updates to their execution state. This makes those updates safer, which should make the execution status more reliable. #5358

  Contributed by @khushboobhatia01

* Fix "not iterable" error for ``output_schema`` handling. If a schema is not well-formed, we ignore it.
  Also, if action output is anything other than a JSON object, we do not try to process it any more.
  ``output_schema`` will change in a future release to support non-object output. #5309

  Contributed by @guzzijones

* ``core.inject_trigger``: resolve ``trigger`` payload shadowing by deprecating ``trigger`` param in favor of ``trigger_name``.
  ``trigger`` param is still available for backwards compatibility, but will be removed in a future release. #5335 and #5383

  Contributed by @mjtice

3.5.0 - June 23, 2021
---------------------

Added
~~~~~

* Added web header settings for additional security hardening to nginx.conf: X-Frame-Options,
  Strict-Transport-Security, X-XSS-Protection and server-tokens. #5183

  Contributed by @shital.

* Added support for ``limit`` and ``offset`` argument to the ``list_values`` data store
  service method (#5097 and #5171).

  Contributed by @anirudhbagri.

* Various additional metrics have been added to the action runner service to provide for better
  operational visibility. (improvement) #4846

  Contributed by @Kami.

* Added sensor model to list of JSON schemas auto-generated by `make schemasgen` that can be used
  by development tools to validate pack contents. (improvement)

* Added the command line utility `st2-validate-pack` that can be used by pack developers to
  validate pack contents. (improvement)

* Fix a bug in the API and CLI code which would prevent users from being able to retrieve resources
  which contain non-ascii (utf-8) characters in the names / references. (bug fix) #5189

  Contributed by @Kami.

* Fix a bug in the API router code and make sure we return correct and user-friendly error to the
  user in case we fail to parse the request URL / path because it contains invalid or incorrectly
  URL encoded data.

  Previously such errors weren't handled correctly which meant original exception with a stack
  trace got propagated to the user. (bug fix) #5189

  Contributed by @Kami.

* Make redis the default coordinator backend.

* Fix a bug in the pack config loader so that objects covered by an additionalProperties schema
  can use encrypted datastore keys and have their default values applied correctly. #5225

  Contributed by @cognifloyd.

* Add new ``database.compressors`` and ``database.zlib_compression_level`` config option which
  specifies compression algorithms client supports for network / transport level compression
  when talking to MongoDB.

  Actual compression algorithm used will be then decided by the server and depends on the
  algorithms which are supported by the server + client.

  Possible / valid values include: zstd, zlib. Keep in mind that zstandard (zstd) is only supported
  by MongoDB >= 4.2.

  Our official Debian and RPM packages bundle ``zstandard`` dependency by default which means
  setting this value to ``zstd`` should work out of the box as long as the server runs
  MongoDB >= 4.2. #5177

  Contributed by @Kami.

* Add support for compressing the payloads which are sent over the message bus. Compression is
  disabled by default and user can enable it by setting ``messaging.compression`` config option
  to one of the following values: ``zstd``, ``lzma``, ``bz2``, ``gzip``.

  In most cases we recommend using ``zstd`` (zstandard) since it offers best trade off between
  compression ratio and number of CPU cycles spent for compression and compression.

  How this will affect the deployment and throughput is very much user specific (workflow and
  resources available). It may make sense to enable it when generic action trigger is enabled
  and when working with executions with large textual results. #5241

  Contributed by @Kami.

* Mask secrets in output of an action execution in the API if the action has an output schema
  defined and one or more output parameters are marked as secret. #5250

  Contributed by @mahesh-orch.

Changed
~~~~~~~

* All the code has been refactored using black and black style is automatically enforced and
  required for all the new code. (#5156)

  Contributed by @Kami.

* Default nginx config (``conf/nginx/st2.conf``) which is used by the installer and Docker
  images has been updated to only support TLS v1.2 and TLS v1.3 (support for TLS v1.0 and v1.1
  has been removed).

  Keep in mind that TLS v1.3 will only be used when nginx is running on more recent distros
  where nginx is compiled against OpenSSL v1.1.1 which supports TLS 1.3. #5183 #5216

  Contributed by @Kami and @shital.

* Add new ``-x`` argument to the ``st2 execution get`` command which allows
  ``result`` field to be excluded from the output. (improvement) #4846

* Update ``st2 execution get <id>`` command to also display execution ``log`` attribute which
  includes execution state transition information.

  By default ``end_timestamp`` attribute and ``duration`` attribute displayed in the command
  output only include the time it took action runner to finish running actual action, but it
  doesn't include the time it it takes action runner container to fully finish running the
  execution - this includes persisting execution result in the database.

  For actions which return large results, there could be a substantial discrepancy - e.g.
  action itself could finish in 0.5 seconds, but writing data to the database could take
  additional 5 seconds after the action code itself was executed.

  For all purposes until the execution result is  persisted to the database, execution is
  not considered as finished.

  While writing result to the database action runner is also consuming CPU cycles since
  serialization of large results is a CPU intensive task.

  This means that "elapsed" attribute and start_timestamp + end_timestamp will make it look
  like actual action completed in 0.5 seconds, but in reality it took 5.5 seconds (0.5 + 5 seconds).

  Log attribute can be used to determine actual duration of the execution (from start to
  finish). (improvement) #4846

  Contributed by @Kami.

* Various internal improvements (reducing number of DB queries, speeding up YAML parsing, using
  DB object cache, etc.) which should speed up pack action registration between 15-30%. This is
  especially pronounced with packs which have a lot of actions (e.g. aws one).
  (improvement) #4846

  Contributed by @Kami.

* Underlying database field type and storage format for the ``Execution``, ``LiveAction``,
  ``WorkflowExecutionDB``, ``TaskExecutionDB`` and ``TriggerInstanceDB`` database models has
  changed.

  This new format is much faster and efficient than the previous one. Users with larger executions
  (executions with larger results) should see the biggest improvements, but the change also scales
  down so there should also be improvements when reading and writing executions with small and
  medium sized results.

  Our micro and end to benchmarks have shown improvements up to 15-20x for write path (storing
  model in the database) and up to 10x for the read path.

  To put things into perspective - with previous version, running a Python runner action which
  returns 8 MB result would take around ~18 seconds total, but with this new storage format, it
  takes around 2 seconds (in this context, duration means the from the time the execution was
  scheduled to the time the execution model and result was written and available in the database).

  The difference is even larger when working with Orquesta workflows.

  Overall performance improvement doesn't just mean large decrease in those operation timings, but
  also large overall reduction of CPU usage - previously serializing large results was a CPU
  intensive time since it included tons of conversions and transformations back and forth.

  The new format is also around 10-20% more storage efficient which means that it should allows
  for larger model values (MongoDB document size limit is 16 MB).

  The actual change should be fully opaque and transparent to the end users - it's purely a
  field storage implementation detail and the code takes care of automatically handling both
  formats when working with those object.

  Same field data storage optimizations have also been applied to workflow related database models
  which should result in the same performance improvements for Orquesta workflows which pass larger
  data sets / execution results around.

  Trigger instance payload field has also been updated to use this new field type which should
  result in lower CPU utilization and better throughput of rules engine service when working with
  triggers with larger payloads.

  This should address a long standing issue where StackStorm was reported to be slow and CPU
  inefficient with handling large executions.

  If you want to migrate existing database objects to utilize the new type, you can use
  ``st2common/bin/migrations/v3.5/st2-migrate-db-dict-field-values`` migration
  script. (improvement) #4846

  Contributed by @Kami.

* Add new ``result_size`` field to the ``ActionExecutionDB`` model. This field will only be
  populated for executions which utilize new field storage format.

  It holds the size of serialzed execution result field in bytes. This field will allow us to
  implement more efficient execution result retrieval and provide better UX since we will be
  able to avoid loading execution results in the WebUI for executions with very large results
  (which cause browser to freeze). (improvement) #4846

  Contributed by @Kami.

* Add new ``/v1/executions/<id>/result[?download=1&compress=1&pretty_format=1]`` API endpoint
  which can be used used to retrieve or download raw execution result as (compressed) JSON file.

  This endpoint will primarily be used by st2web when executions produce very large results so
  we can avoid loading, parsing and formatting those very large results as JSON in the browser
  which freezes the browser window / tab. (improvement) #4846

  Contributed by @Kami.

* Update ``jinja2`` dependency to the latest stable version (2.11.3). #5195

* Update ``pyyaml`` dependency to the latest stable version (5.4). #5207

* Update various dependencies to latest stable versions (``bcrypt``, ``appscheduler``, ``pytz``,
  ``python-dateutil``, ``psutil``, ``passlib``, ``gunicorn``, ``flex``, ``cryptography``.
  ``eventlet``, ``greenlet``, ``webob`` , ``mongoengine``, ``pymongo``, ``requests``,
  ``pyyaml``, ``kombu``, ``amqp``, ``python-ldap``).

  #5215, https://github.com/StackStorm/st2-auth-ldap/pull/94

  Contributed by @Kami.

* Update code and dependencies so it supports Python 3.8 and Mongo DB 4.4 #5177

  Contributed by @nzloshm @winem @Kami.

* StackStorm Web UI (``st2web``) has been updated to not render and display execution results
  larger than 200 KB directly in the history panel in the right side bar by default anymore.
  Instead a link to view or download the raw result is displayed.

  Execution result widget was never optimized to display very large results (especially for
  executions which return large nested dictionaries) so it would freeze and hang the whole
  browser tab / window when trying to render / display large results.

  If for some reason you want to revert to the old behavior (this is almost never a good idea
  since it will cause browser to freeze when trying to display large results), you can do that by
  setting ``max_execution_result_size_for_render`` option in the config to a very large value (e.g.
  ``max_execution_result_size_for_render: 16 * 1024 * 1024``).

  https://github.com/StackStorm/st2web/pull/868

  Contributed by @Kami.

* Some of the config option registration code has been refactored to ignore "option already
  registered" errors. That was done as a work around for an occasional race in the tests and
  also to make all of the config option registration code expose the same consistent API. #5234

  Contributed by @Kami.

* Update ``pyywinrm`` dependency to the latest stable version (0.4.1). #5212

  Contributed by @chadpatt .

* Monkey patch on st2stream earlier in flow #5240

  Contributed by Amanda McGuinness (@amanda11 Ammeon Solutions)

* Support % in CLI arguments by reading the ConfigParser() arguments with raw=True.

  This removes support for '%' interpolations on the configuration arguments.

  See https://docs.python.org/3.8/library/configparser.html#configparser.ConfigParser.get for
  further details. #5253

  Contributed by @winem.

* Remove duplicate host header in the nginx config for the auth endpoint.

* Update orquesta to v1.4.0.

Improvements
~~~~~~~~~~~~

* CLI has been updated to use or ``orjson`` when parsing API response and C version of the YAML
  safe dumper when formatting execution result for display. This should result in speed up when
  displaying execution result (``st2 execution get``, etc.) for executions with large results.

  When testing it locally, the difference for execution with 8 MB result was 18 seconds vs ~6
  seconds. (improvement) #4846

  Contributed by @Kami.

* Update various Jinja functiona to utilize C version of YAML ``safe_{load,dump}`` functions and
  orjson for better performance. (improvement) #4846

  Contributed by @Kami.

* For performance reasons, use ``udatetime`` library for parsing ISO8601 / RFC3339 date strings
  where possible. (improvement) #4846

  Contributed by @Kami.

* Speed up service start up time by speeding up runners registration on service start up by
  re-using existing stevedore ``ExtensionManager`` instance instead of instantiating new
  ``DriverManager`` instance per extension which is not necessary and it's slow since it requires
  disk / pkg resources scan for each extension. (improvement) #5198

  Contributed by @Kami.

* Add new ``?max_result_size`` query parameter filter to the ``GET /v1/executiond/<id>`` API
  endpoint.

  This query parameter allows clients to implement conditional execution result retrieval and
  only retrieve the result field if it's smaller than the provided value.

  This comes handy in the various client scenarios (such as st2web) where we don't display and
  render very large results directly since it allows to speed things up and decrease amount of
  data retrieved and parsed. (improvement) #5197

  Contributed by @Kami.

* Update default nginx config which is used for proxying API requests and serving static
  content to only allow HTTP methods which are actually used by the services (get, post, put,
  delete, options, head).

  If a not-allowed method is used, nginx will abort the request early and return 405 status
  code. #5193

  Contributed by @ashwini-orchestral

* Update default nginx config which is used for proxying API requests and serving static
  content to not allow range requests. #5193

  Contributed by @ashwini-orchestral

* Drop unused python dependencies: prometheus_client, python-gnupg, more-itertools, zipp. #5228

  Contributed by @cognifloyd.

* Update majority of the "resource get" CLI commands (e.g. ``st2 execution get``,
  ``st2 action get``, ``st2 rule get``, ``st2 pack get``, ``st2 apikey get``, ``st2 trace get``,
  ``st2 key get``, ``st2 webhook get``, ``st2  timer get``, etc.) so they allow for retrieval
  and printing of information for multiple resources using the following notation:
  ``st2 <resource> get <id 1> <id 2> <id n>``, e.g. ``st2 action.get pack.show packs.get
  packs.delete``

  This change is fully backward compatible when retrieving only a single resource (aka single
  id is passed to the command).

  When retrieving a single source the command will throw and exit with non-zero if a resource is
  not found, but when retrieving multiple resources, command will just print an error and
  continue with printing the details of any other found resources. (new feature) #4912

  Contributed by @Kami.

Fixed
~~~~~

* Refactor spec_loader util to use yaml.load with SafeLoader. (security)
  Contributed by @ashwini-orchestral

* Import ABC from collections.abc for Python 3.10 compatibility. (#5007)
  Contributed by @tirkarthi

* Updated to use virtualenv 20.4.0/PIP20.3.3 and fixate-requirements to work with PIP 20.3.3 #512
  Contributed by Amanda McGuinness (@amanda11 Ammeon Solutions)

* Fix ``st2 execution get --with-schema`` flag.  (bug fix) #4846

  Contributed by @Kami.

* Fix SensorTypeAPI schema to use class_name instead of name since documentation for pack
  development uses class_name and registrar used to load sensor to database assign class_name
  to name in the database model. (bug fix)

* Updated paramiko version to 2.7.2, to go with updated cryptography to prevent problems
  with ssh keys on remote actions. #5201

  Contributed by Amanda McGuinness (@amanda11 Ammeon Solutions)

* Update rpm package metadata and fix ``Provides`` section for RHEL / CentOS 8 packages.

  In the previous versions, RPM metadata would incorrectly signal that the ``st2`` package
  provides various Python libraries which it doesn't (those Python libraries are only used
  internally for the package local virtual environment).

  https://github.com/StackStorm/st2-packages/pull/697

  Contributed by @Kami.

* Make sure ``st2common.util.green.shell.run_command()`` doesn't leave stray / zombie processes
  laying around in some command timeout scenarios. #5220

  Contributed by @r0m4n-z.

* Fix support for skipping notifications for workflow actions. Previously if action metadata
  specified an empty list for ``notify`` parameter value, that would be ignored / not handled
  correctly for workflow (orquesta, action chain) actions. #5221 #5227

  Contributed by @khushboobhatia01.

* Clean up to remove unused methods in the action execution concurrency policies. #5268

3.4.1 - March 14, 2021
----------------------

Added
~~~~~


* Service start up code has been updated to log a warning if a non-utf-8 encoding / locale is
  detected.

  Using non-utf-8 locale while working with unicode data will result in various issues so users
  are strongly recommended to ensure encoding for all the StackStorm service is
  set to ``utf-8``. (#5182)

  Contributed by @Kami.

Changed
~~~~~~~

* Use `sudo -E` to fix GitHub Actions tests #5187

  Contributed by @cognifloyd

Fixed
~~~~~

* Properly handle unicode strings in logs #5184

  Fix a logging loop when attempting to encode Unicode characters in locales that do not support
  Unicode characters - CVE-2021-28667.

  See https://stackstorm.com/2021/03/10/stackstorm-v3-4-1-security-fix/ for more information.

  Contributed by @Kami

* Fix SensorTypeAPI schema to use class_name instead of name since documentation for pack
  development uses class_name and registrar used to load sensor to database assign class_name
  to name in the database model. (bug fix)

* Updated paramiko version to 2.7.2, to go with updated cryptography to prevent problems
  with ssh keys on remote actions. #5201

  Contributed by Amanda McGuinness (@amanda11 Ammeon Solutions)

3.4.0 - March 02, 2021
----------------------

Added
~~~~~

* Added support for GitLab SSH URLs on pack install and download actions. (improvement) #5050
  Contributed by @asthLucas

* Added st2-rbac-backend pip requirements for RBAC integration. (new feature) #5086
  Contributed by @hnanchahal

* Added notification support for err-stackstorm. (new feature) #5051

* Added st2-auth-ldap pip requirements for LDAP auth integartion. (new feature) #5082
  Contributed by @hnanchahal

* Added --register-recreate-virtualenvs flag to st2ctl reload to recreate virtualenvs from
  scratch. (part of upgrade instructions) #5167

  Contributed by @winem and @blag

Changed
~~~~~~~

* Updated deprecation warning for python 2 pack installs, following python 2 support removal. #5099
  Contributed by @amanda11

* Improve the st2-self-check script to echo to stderr and exit if it isn't run with a
  ST2_AUTH_TOKEN or ST2_API_KEY environment variable. (improvement) #5068

* Added timeout parameter for packs.install action to help with long running installs that exceed the
  default timeout of 600 sec which is defined by the python_script action runner (improvement) #5084

  Contributed by @hnanchahal

* Upgraded cryptography version to 3.2 to avoid CVE-2020-25659 (security) #5095

* Converted most CI jobs from Travis to GitHub Actions (all except Integration tests).

  Contributed by @nmaludy, @winem, and @blag

* Updated cryptography dependency to version 3.3.2 to avoid CVE-2020-36242 (security) #5151

* Update most of the code in the StackStorm API and services layer to utilize ``orjson`` library
  for serializing and de-serializing json.

  That should result in better json serialization and deserialization performance.

  The change should be fully backward compatible, only difference is that API JSON responses now
  won't be indented using 4 spaces by default (indenting adds unnecessary overhead and if needed,
  the response can be pretty formatted on the client side using ``jq`` or similar). (improvement)
  #5153

  Contributed by @Kami

Fixed
~~~~~

* Pin chardet version as newest version was incompatible with pinned requests version #5101
  Contributed by @amanda11

* Fixed issue were st2tests was not getting installed using pip because no version was specified.
  Contributed by @anirudhbagri

* Added monkey patch fix to st2stream to enable it to work with mongodb via SSL. (bug fix) #5078 #5091

* Fix nginx buffering long polling stream to client.  Instead of waiting for closed connection
  wait for final event to be sent to client. (bug fix) #4842  #5042

  Contributed by @guzzijones

* StackStorm now explicitly decodes pack files as utf-8 instead of implicitly as ascii (bug fix)
  #5106, #5107

* Fix incorrect array parameter value casting when executing action via chatops or using
  ``POST /aliasexecution/match_and_execute`` API endpoint. The code would incorrectly assume the
  value is always a string, but that may not be the cast - they value could already be a list and
  in this case we don't want any casting to be performed. (bug fix) #5141

  Contributed by @Kami.

* Fix ``@parameter_name=/path/to/file/foo.json`` notation in the ``st2 run`` command which didn't
  work correctly because it didn't convert read bytes to string / unicode type. (bug fix) #5140

  Contributed by @Kami.

* Fix broken ``st2 action-alias execute`` command and make sure it works
  correctly. (bug fix) #5138

  Contributed by @Kami.

Removed
~~~~~~~

* Removed --python3 pack install option  #5100
  Contributed by @amanda11

* Removed submit-debug-info tool and the st2debug component #5103

* Removed check-licence script (cleanup) #5092

  Contributed by @kroustou

* Updated Makefile and CI to use Python 3 only, removing Python 2 (cleanup) #5090

  Contributed by @blag

* Remove st2resultstracker from st2ctl, the development environment and the st2actions setup.py (cleanup) #5108

  Contributed by @winem

3.3.0 - October 06, 2020
------------------------

Added
~~~~~
* Add make command to autogen JSON schema from the models of action, rule, etc. Add check
  to ensure update to the models require schema to be regenerated. (new feature)
* Improved st2sensor service logging message when a sensor will not be loaded when assigned to a
  different partition (@punkrokk) #4991
* Add support for a configurable connect timeout for SSH connections as requested in #4715
  by adding the new configuration parameter ``ssh_connect_timeout`` to the ``ssh_runner``
  group in st2.conf. (new feature) #4914

  This option was requested by Harry Lee (@tclh123) and contributed by Marcel Weinberg (@winem).
* Added a FAQ for the default user/pass for the `tools/launch_dev.sh` script and print out the
  default pass to screen when the script completes. (improvement) #5013

  Contributed by @punkrokk
* Added deprecation warning if attempt to install or download a pack that only supports
  Python 2. (new feature) #5037

  Contributed by @amanda11
* Added deprecation warning to each StackStorm service log, if service is running with
  Python 2. (new feature) #5043

  Contributed by @amanda11
* Added deprecation warning to st2ctl, if st2 python version is Python 2. (new feature) #5044

  Contributed by @amanda11

Changed
~~~~~~~

* Switch to MongoDB ``4.0`` as the default version starting with all supported OS's in st2
  ``v3.3.0`` (improvement) #4972

  Contributed by @punkrokk

* Added an enhancement where ST2api.log no longer reports the entire traceback when trying to get a datastore value
  that does not exist. It now reports a simplified log for cleaner reading. Addresses and Fixes #4979. (improvement) #4981

  Contributed by Justin Sostre (@saucetray)
* The built-in ``st2.action.file_writen`` trigger has been renamed to ``st2.action.file_written``
  to fix the typo (bug fix) #4992
* Renamed reference to the RBAC backend/plugin from ``enterprise`` to ``default``. Updated st2api
  validation to use the new value when checking RBAC configuration. Removed other references to
  enterprise for RBAC related contents. (improvement)
* Remove authentication headers ``St2-Api-Key``, ``X-Auth-Token`` and ``Cookie`` from webhook payloads to
  prevent them from being stored in the database. (security bug fix) #4983

  Contributed by @potato and @knagy
* Updated orquesta to version v1.2.0.

Fixed
~~~~~

* Fixed a bug where `type` attribute was missing for netstat action in linux pack. Fixes #4946

  Reported by @scguoi and contributed by Sheshagiri (@sheshagiri)

* Fixed a bug where persisting Orquesta to the MongoDB database returned an error
  ``message: key 'myvar.with.period' must not contain '.'``. This happened anytime an
  ``input``, ``output``, ``publish`` or context ``var`` contained a key with a ``.`` within
  the name (such as with hostnames and IP addresses). This was a regression introduced by
  trying to improve performance. Fixing this bug means we are sacrificing performance of
  serialization/deserialization in favor of correctness for persisting workflows and
  their state to the MongoDB database. (bug fix) #4932

  Contributed by Nick Maludy (@nmaludy Encore Technologies)
* Fix a bug where passing an empty list to a with items task in a subworkflow causes
  the parent workflow to be stuck in running status. (bug fix) #4954
* Fixed a bug in the example nginx HA template declared headers twice (bug fix) #4966
  Contributed by @punkrokk

* Fixed a bug in the ``paramiko_ssh`` runner where SSH sockets were not getting cleaned
  up correctly, specifically when specifying a bastion host / jump box. (bug fix) #4973

  Contributed by Nick Maludy (@nmaludy Encore Technologies)
* Fixed a bytes/string encoding bug in the ``linux.dig`` action so it should work on Python 3
  (bug fix) #4993

* Fixed a bug where a python3 sensor using ssl needs to be monkey patched earlier. See also #4832, #4975 and gevent/gevent#1016 (bug fix) #4976

  Contributed by @punkrokk
* Fixed bug where action information in RuleDB object was not being parsed properly
  because mongoengine EmbeddedDocument objects were added to JSON_UNFRIENDLY_TYPES and skipped.
  Removed this and added if to use to_json method so that mongoengine EmbeddedDocument
  are parsed properly.

  Contributed by Bradley Bishop (@bishopbm1 Encore Technologies)
* Fix a regression when updated ``dnspython`` pip dependency resulted in
  st2 services unable to connect to mongodb remote host (bug fix) #4997
* Fixed a regression in the ``linux.dig`` action on Python 3. (bug fix) #4993

  Contributed by @blag
* Fixed a bug in pack installation logging code where unicode strings were not being
  interpolated properly. (bug fix)

  Contributed by @misterpah
* Fixed a compatibility issue with the latest version of the ``logging`` library API
  where the ``find_caller()`` function introduced some new variables. (bug fix) #4923

  Contributed by @Dahfizz9897
* Fixed another logging compatibility issue with the ``logging`` API in Python 3.
  The return from the ``logging.findCaller()`` implementation now expects a 4-element
  tuple. Also, in Python 3 there are new arguments that are passed in and needs to be
  acted upon, specificall ``stack_info`` that determines the new 4th element in the returned
  tuple. (bug fix) #5057

  Contributed by Nick Maludy (@nmaludy Encore Technologies)

Removed
~~~~~~~

* Removed ``Mistral`` workflow engine (deprecation) #5011

  Contributed by Amanda McGuinness (@amanda11 Ammeon Solutions)
* Removed ``CentOS 6``/``RHEL 6`` support #4984

  Contributed by Amanda McGuinness (@amanda11 Ammeon Solutions)
* Removed our fork of ``codecov-python`` for CI and have switched back to the upstream version (improvement) #5002

3.2.0 - April 27, 2020
----------------------

Added
~~~~~
* Add support for blacklisting / whitelisting hosts to the HTTP runner by adding new
  ``url_hosts_blacklist`` and ``url_hosts_whitelist`` runner attribute. (new feature)
  #4757
* Add ``user`` parameter to ``re_run`` method of st2client. #4785
* Install pack dependencies automatically. #4769
* Add support for ``immutable_parameters`` on Action Aliases. This feature allows default
  parameters to be supplied to the action on every execution of the alias. #4786
* Add ``get_entrypoint()`` method to ``ActionResourceManager`` attribute of st2client.
  #4791
* Add support for orquesta task retry. (new feature)
* Add config option ``scheduler.execution_scheduling_timeout_threshold_min`` to better control the cleanup of scheduled actions that were orphaned. #4886

Changed
~~~~~~~
* Install pack with the latest tag version if it exists when branch is not specialized.
  (improvement) #4743
* Implement "continue" engine command to orquesta workflow. (improvement) #4740
* Update various internal dependencies to latest stable versions (apscheduler, eventlet,
  kombu, amqp, pyyaml, mongoengine, python-gnupg, paramiko, tooz, webob, bcrypt).

  Latest version of mongoengine should show some performance improvements (5-20%) when
  writing very large executions (executions with large results) to the database. #4767
* Improved development instructions in requirements.txt and dist_utils.py comment headers
  (improvement) #4774
* Add new ``actionrunner.stream_output_buffer_size`` config option and default it to ``-1``
  (previously default value was ``0``). This should result in a better performance and smaller
  CPU utilization for Python runner actions which produce a lot of output.
  (improvement)

  Reported and contributed by Joshua Meyer (@jdmeyer3) #4803
* Add new ``action_runner.pip_opts`` st2.conf config option which allows user to specify a list
  of command line option which are passed to ``pip install`` command when installing pack
  dependencies into a pack specific virtual environment. #4792
* Refactor how orquesta handles individual item result for with items task. Before the fix,
  when there are a lot of items and/or result size for each item is huge, there is a negative
  performance impact on write to the database when recording the conductor state. (improvement)
* Remove automatic rendering of workflow output when updating task state for orquesta workflows.
  This caused workflow output to render incorrectly in certain use case. The render_workflow_output
  function must be called separately. (improvement)
* Update various internal dependencies to latest stable versions (cryptography, jinja2, requests,
  apscheduler, eventlet, amqp, kombu, semver, six) #4819 (improvement)
* Improve MongoDB connection timeout related code. Connection and server selection timeout is now
  set to 3 seconds. Previously a default value of 30 seconds was used which means that for many
  connection related errors, our code would first wait for this timeout to be reached (30 seconds)
  before returning error to the end user. #4834
* Upgrade ``pymongo`` to the latest stable version (``3.10.0.``). #4835 (improvement)
* Updated Paramiko to v2.7.1 to support new PEM ECDSA key formats #4901 (improvement)
* Remove ``.scrutinizer.yml`` config file. No longer used.
* Convert escaped dict and dynamic fields in workflow db models to normal dict and dynamic fields.
  (performnce improvement)
* Add support for `PEP 508 <https://www.python.org/dev/peps/pep-0508/#environment-markers>`_
  environment markers in generated ``requirements.txt`` files. (improvement) #4895
* Use ``pip-compile`` from ``pip-tools`` instead of ``pip-conflict-checker`` (improvement) #4896
* Refactor how inbound criteria for join task in orquesta workflow is evaluated to count by
  task completion instead of task transition. (improvement)
* The workflow engine orquesta is updated to v1.1.0 for the st2 v3.2 release. The version upgrade
  contains various new features and bug fixes. Please review the release notes for the full list of
  changes at https://github.com/StackStorm/orquesta/releases/tag/v1.1.0 and the st2 upgrade notes
  for potential impact. (improvement)
* Update st2 nginx config to remove deprecated ``ssl on`` option. #4917 (improvement)
* Updated and tested tooz to v2.8.0 to apply fix for consul coordination heartbeat (@punkrokk @winem) #5121

Fixed
~~~~~
* Fix a typo that caused an internal server error when filtering actions by tags. Fixes #4918

  Reported by @mweinberg-cm and contributed by Marcel Weinberg (@winem)

* Fix the action query when filtering tags. The old implementation returned actions which have the
  provided name as action name and not as tag name. (bug fix) #4828

  Reported by @AngryDeveloper and contributed by Marcel Weinberg (@winem)
* Fix the passing of arrays to shell scripts where the arrays where not detected as such by the
  st2 action_db utility. This caused arrays to be passed as Python lists serialized into a string.

  Reported by @kingsleyadam #4804 and contributed by Marcel Weinberg (@winem) #4861
* Fix ssh zombies when using ProxyCommand from ssh config #4881 [Eric Edgar]
* Fix rbac with execution view where the rbac is unable to verify the pack or uid of the execution
  because it was not returned from the action execution db. This would result in an internal server
  error when trying to view the results of a single execution.
  Contributed by Joshua Meyer (@jdmeyer3) #4758
* Fixed logging middleware to output a ``content_length`` of ``0`` instead of ``Infinity``
  when the type of data being returned is not supported. Previously, when the value was
  set to ``Infinity`` this would result in invalid JSON being output into structured
  logs. (bug fix) #4722

  Contributed by Nick Maludy (@nmaludy Encore Technologies)
* Fix the workflow execution cancelation to proceed even if the workflow execution is not found or
  completed. (bug fix) #4735
* Added better error handling to ``contrib/linux/actions/dig.py`` to inform if dig is not installed.
  Contributed by JP Bourget (@punkrokk Syncurity) #4732
* Update ``dist_utils`` module which is bundled with ``st2client`` and other Python packages so it
  doesn't depend on internal pip API and so it works with latest pip version. (bug fix) #4750
* Fix dependency conflicts in pack CI runs: downgrade requests dependency back to 0.21.0, update
  internal dependencies and test expectations (amqp, pyyaml, prance, six) (bugfix) #4774
* Fix secrets masking in action parameters section defined inside the rule when using
  ``GET /v1/rules`` and ``GET /v1/rules/<ref>`` API endpoint. (bug fix) #4788 #4807

  Contributed by @Nicodemos305 and @jeansfelix
* Fix a bug with authentication API endpoint (``POST /auth/v1/tokens``) returning internal
  server error when running under gunicorn and when``auth.api_url`` config option was not set.
  (bug fix) #4809

  Reported by @guzzijones
* Fixed ``st2 execution get`` and ``st2 run`` not printing the ``action.ref`` for non-workflow
  actions. (bug fix) #4739

  Contributed by Nick Maludy (@nmaludy Encore Technologies)
* Update ``st2 execution get`` command to always include ``context.user``, ``start_timestamp`` and
  ``end_timestamp`` attributes. (improvement) #4739

* Fixed ``core.sendmail`` base64 encoding of longer subject lines (bug fix) #4795

  Contributed by @stevemuskiewicz and @guzzijones
* Update all the various rule criteria comparison operators which also work with strings (equals,
  icontains, nequals, etc.) to work correctly on Python 3 deployments if one of the operators is
  of a type bytes and the other is of a type unicode / string. (bug fix) #4831
* Fix SSL connection support for MongoDB and RabbitMQ which wouldn't work under Python 3 and would
  result in cryptic "maximum recursion depth exceeded while calling a Python object" error on
  connection failure.

  NOTE: This issue only affected installations using Python 3. (bug fix) #4832 #4834

  Reported by @alexku7.
* Fix the amqp connection setup for WorkflowExecutionHandler to pass SSL params. (bug fix) #4845

  Contributed by Tatsuma Matsuki (@mtatsuma)

* Fix dependency conflicts by updating ``requests`` (2.23.0) and ``gitpython`` (2.1.15). #4869
* Fix orquesta syntax error for with items task where action is misindented or missing. (bug fix)
  PR StackStorm/orquesta#195.
* Fix orquesta yaql/jinja vars extraction to ignore methods of base ctx() dict. (bug fix)
  PR StackStorm/orquesta#196. Fixes #4866.
* Fix parsing of array of dicts in YAQL functions. Fix regression in YAQL/Jinja conversion
  functions as a result of the change. (bug fix) PR StackStorm/orquesta#191.

  Contributed by Hiroyasu Ohyama (@userlocalhost)
* Fix retry in orquesta when a task that has a transition on failure will also be traversed on
  retry. (bug fix) PR StackStorm/orquesta#200

Removed
~~~~~~~

* Removed Ubuntu 14.04 from test matrix #4897

3.1.0 - June 27, 2019
---------------------

Changed
~~~~~~~

* Allow the orquesta st2kv function to return default for nonexistent key. (improvement) #4678
* Update requests library to latest version (2.22.0) in requirements. (improvement) #4680
* Disallow "decrypt_kv" filter to be specified in the config for values that are marked as
  "secret: True" in the schema. (improvement) #4709
* Upgrade ``tooz`` library to latest stable version (1.65.0) so it uses latest version of
  ``grpcio`` library. (improvement) #4713
* Update ``st2-pack-install`` and ``st2-pack-download`` CLI command so it supports installing
  packs from local directories which are not git repositories. (improvement) #4713

Fixed
~~~~~

* Fix orquesta st2kv to return empty string and null values. (bug fix) #4678
* Allow tasks defined in the same task transition with ``fail`` to run for orquesta. (bug fix)
* Fix workflow service to handle unexpected coordinator and database errors. (bug fix) #4704 #4705
* Fix filter ``to_yaml_string`` to handle mongoengine base types for dict and list. (bug fix) #4700
* Fix timeout handling in the Python runner. In some scenarios where action would time out before
  producing any output (stdout, stder), timeout was not correctly propagated to the user. (bug fix)
  #4713
* Update ``st2common/setup.py`` file so it correctly declares all the dependencies and script
  files it provides. This way ``st2-pack-*`` commands can be used in a standalone fashion just by
  installing ``st2common`` Python package and nothing else. (bug fix) #4713
* Fix ``st2-pack-download`` command so it works in the environments where ``sudo`` binary is not
  available (e.g. Docker). (bug fix) #4713

3.0.1 - May 24, 2019
--------------------

Fixed
~~~~~

* Fix a bug in the remote command and script runner so it correctly uses SSH port from a SSH config
  file if ``ssh_runner.use_ssh_config`` parameter is set to ``True`` and if a custom (non-default)
  value for SSH port is specified in the configured SSH config file
  (``ssh_runner.ssh_config_file_path``). (bug fix) #4660 #4661
* Update pack install action so it works correctly when ``python_versions`` ``pack.yaml`` metadata
  attribute is used in combination with ``--use-python3`` pack install flag. (bug fix) #4654 #4662
* Add ``source_channel`` back to the context used by Mistral workflows for executions which are
  triggered via ChatOps (using action alias).

  In StackStorm v3.0.0, this variable was inadvertently removed from the context used by Mistral
  workflows. (bug fix) #4650 #4656
* Fix a bug with ``timestamp`` attribute in the ``execution.log`` attribute being incorrect when
  server time where st2api is running was not set to UTC. (bug fix) #4668

  Contributed by Igor Cherkaev. (@emptywee)
* Fix a bug with some packs which use ``--use-python3`` flag (running Python 3 actions on installation
  where StackStorm components run under Python 2) which rely on modules from Python 3 standard
  library which are also available in Python 2 site-packages (e.g. ``concurrent``) not working
  correctly.

  In such scenario, package / module was incorrectly loaded from Python 2 site-packages instead of
  Python 3 standard library which broke such packs. (bug fix) #4658 #4674
* Remove policy-delayed status to avoid bouncing between delayed statuses. (bug fix) #4655
* Fix a possible shell injection in the ``linux.service`` action. User who had access to run this
  action could cause a shell command injection by passing a compromised value for either the
  ``service`` or ``action`` parameter. (bug fix) #4675

  Reported by James Robinson (Netskope and Veracode).
* Replace ``sseclient`` library on which CLI depends on with ``sseclient-py``. ``sseclient`` has
  various issue which cause client to sometimes hang and keep the connection open which also causes
  ``st2 execution tail`` command to sometimes hang for a long time. (improvement)
* Truncate some database index names so they are less than 65 characters long in total. This way it
  also works with AWS DocumentDB which doesn't support longer index name at the moment.

  NOTE: AWS DocumentDB is not officially supported. Use at your own risk. (improvement) #4688 #4690

  Reported by Guillaume Truchot (@GuiTeK)

3.0.0 - April 18, 2019
----------------------

Added
~~~~~

* Allow access to user-scoped datastore items using ``{{ st2kv.user.<key name> }}`` Jinja template
  notation inside the action parameter default values. (improvement) #4463

  Contributed by Hiroyasu OHYAMA (@userlocalhost).
* Add support for new ``python_versions`` (``list`` of ``string``) attribute to pack metadata file
  (``pack.yaml``). With this attribute pack declares which major Python versions it supports and
  works with (e.g. ``2`` and ``3``).

  For backward compatibility reasons, if pack metadata file doesn't contain that attribute, it's
  assumed it only works with Python 2. (new feature) #4474
* Update service bootstrap code and make sure all the services register in a service registry once
  they come online and become available.

  This functionality is only used internally and will only work if configuration backend is
  correctly configured in ``st2.conf`` (new feature) #4548
* Add new ``GET /v1/service_registry/groups`` and
  ``GET /v1/service_registry/groups/<group_id>/members`` API endpoint for listing available service
  registry groups and members.

  Also add corresponding CLI commands - ``st2 service-registry group list``, ``st2 service registry
  member list [--group-id=<group id>]``

  NOTE: This API endpoint is behind an RBAC wall and can only be viewed by the admins. (new feature)
  #4548
* Add support for ``?include_attributes`` and ``?exclude_attributes`` query param filter to the
  ``GET /api/v1/executions/{id}`` API endpoint. Also update ``st2 execution get`` CLI command so it
  only retrieves attributes which are displayed. (new feature) #4497

  Contributed by Nick Maludy (@nmaludy Encore Technologies)

* Add new ``--encrypted`` flag to ``st2 key set`` CLI command that allows users to pass in values
  which are already encrypted.

  This attribute signals the API that the value is already encrypted and should be used as-is.

  ``st2 key load`` CLI command has also been updated so it knows how to work with values which are
  already encrypted. This means that ``st2 key list -n 100 -j < data.json ; st2 key load
  data.json`` will now also work out of the box for encrypted datastore values (values which have
  ``encrypted: True`` and ``secret: True`` attribute will be treated as already encrypted and used
  as-is).

  The most common use case for this feature is migrating / restoring datastore values from one
  StackStorm instance to another which uses the same crypto key.

  Contributed by Nick Maludy (Encore Technologies) #4547
* Add ``source_channel`` to Orquesta ``st2()`` context for workflows called via ChatOps. #4600

Changed
~~~~~~~

* Changed the ``inquiries`` API path from ``/exp`` to ``/api/v1``. #4495
* Refactored workflow state in orquesta workflow engine. Previously, state in the workflow engine
  is not status to be consistent with st2. Other terminologies used in the engine are also revised
  to make it easier for developers to understand. (improvement)
* Update Python runner code so it prioritizes libraries from pack virtual environment over StackStorm
  system dependencies.

  For example, if pack depends on ``six==1.11.0`` in pack ``requirements.txt``, but StackStorm depends
  on ``six==1.10.0``, ``six==1.11.0`` will be used when running Python actions from that pack.

  Keep in mind that will not work correctly if pack depends on a library which brakes functionality used
  by Python action wrapper code.

  Contributed by Hiroyasu OHYAMA (@userlocalhost). #4571
* Improved the way that the ``winrm-ps-script`` runner sends scripts to the target Windows
  host. Previously the script was read from the local filesystem and serialized as one long
  command executed on the command line. This failed when the script was longer than either
  2047 or 8191 bytes (depending on Windows version) as the Windows command line uses this
  as its maximum length. To overcome this, the ``winrm-ps-script`` runner now uploads the
  script into a temporary directory on the target host, then executes the script.
  (improvement) #4514

  Contributed by Nick Maludy (Encore Technologies)
* Update various internal dependencies to latest stable versions (apscheduler, pyyaml, kombu,
  mongoengine, pytz, stevedore, python-editor, jinja2). #4610
* Update logging code so we exclude log messages with log level ``AUDIT`` from a default service
  log file (e.g. ``st2api.log``). Log messages with level ``AUDIT`` are already logged in a
  dedicated service audit log file (e.g. ``st2api.audit.log``) so there is no need for them to also
  be duplicated and included in regular service log file.

  NOTE: To aid with debugging, audit log messages are also included in a regular log file when log
  level is set to ``DEBUG`` or ``system.debug`` config option is set to ``True``.

  Reported by Nick Maludy. (improvement) #4538 #4502 #4621
* Add missing ``--user`` argument to ``st2 execution list`` CLI command. (improvement) #4632

  Contributed by Tristan Struthers (@trstruth).
* Update ``decrypt_kv`` Jinja template filter so it to throws a more user-friendly error message
  when decryption fails because the variable references a datastore value which doesn't exist.
  (improvement) #4634
* Updated orquesta to v0.5. (improvement)

Fixed
~~~~~

* Refactored orquesta execution graph to fix performance issue for workflows with many references
  to non-join tasks. st2workflowengine and DB models are refactored accordingly. (improvement)
  StackStorm/orquesta#122.
* Fix orquesta workflow stuck in running status when one or more items failed execution for a with
  items task. (bug fix) #4523
* Fix orquesta workflow bug where context variables are being overwritten on task join. (bug fix)
  StackStorm/orquesta#112
* Fix orquesta with items task performance issue. Workflow runtime increase significantly when a
  with items task has many items and result in many retries on write conflicts. A distributed lock
  is acquired before write operations to avoid write conflicts. (bug fix) Stackstorm/orquesta#125
* Fix a bug with some API endpoints returning 500 internal server error when an exception contained
  unicode data. (bug fix) #4598
* Fix the ``st2 workflow inspect`` command so it correctly passes authentication token. (bug fix)
  #4615
* Fix an issue with new line characters (``\n``) being converted to ``\r\n`` in remote shell
  command and script actions which use sudo. (bug fix) #4623
* Update service bootstrap and ``st2-register-content`` script code so non-fatal errors are
  suppressed by default and only logged under ``DEBUG`` log level. (bug fix) #3933 #4626 #4630
* Fix a bug with not being able to decrypt user-scoped datastore values inside Jinja expressions
  using ``decrypt_kv`` Jinja filter. (bug fix) #4634

  Contributed by Hiroyasu OHYAMA (@userlocalhost).
* Fix a bug with user-scoped datastore values not working inside action-chain workflows. (bug fix)
  #4634
* Added missing parameter types to ``linux.wait_for_ssh`` action metadata. (bug fix) #4611
* Fix HTTP runner (``http-request``) so it works correctly with unicode (non-ascii) body payloads.
  (bug fix) #4601 #4599

  Reported by Carlos Santana (@kknyxkk) and Rafael Martins (@rsmartins78).
* Fix ``st2-self-check`` so it sets correct permissions on pack directories which it copies over
  to ``/opt/stackstorm/packs``. (bug fix) #4645
* Fix ``POST /v1/actions`` API endpoint to throw a more user-friendly error when writing data file
  to disk fails because of incorrect permissions. (bug fix) #4645

2.10.4 - March 15, 2019
-----------------------

Fixed
~~~~~

* Fix inadvertent regression in notifier service which would cause generic action trigger to only
  be dispatched for completed states even if custom states were specified using
  ``action_sensor.emit_when`` config option. (bug fix)
  Reported by Shu Sugimoto (@shusugmt). #4591
* Make sure we don't log auth token and api key inside st2api log file if those values are provided
  via query parameter and not header (``?x-auth-token=foo``, ``?st2-api-key=bar``). (bug fix) #4592
  #4589
* Fix rendering of ``{{ config_context. }}`` in orquesta task that references action from a
  different pack (bug fix) #4570 #4567
* Add missing default config location (``/etc/st2/st2.conf``) to the following services:
  ``st2actionrunner``, ``st2scheduler``, ``st2workflowengine``. (bug fix) #4596
* Update statsd metrics driver so any exception thrown by statsd library is treated as non fatal.

  Previously there was an edge case if user used a hostname instead of an IP address for metrics
  backend server address. In such scenario, if hostname DNS resolution failed, statsd driver would
  throw the exception which would propagate all the way up and break the application. (bug fix) #4597

  Reported by Chris McKenzie.

2.10.3 - March 06, 2019
-----------------------

Fixed
~~~~~

* Fix improper CORS where request from an origin not listed in ``allowed_origins`` will be responded
  with ``null`` for the ``Access-Control-Allow-Origin`` header. The fix returns the first of our
  allowed origins if the requesting origin is not a supported origin. Reported by Barak Tawily.
  (bug fix)

2.9.3 - March 06, 2019
-----------------------

Fixed
~~~~~

* Fix improper CORS where request from an origin not listed in ``allowed_origins`` will be responded
  with ``null`` for the ``Access-Control-Allow-Origin`` header. The fix returns the first of our
  allowed origins if the requesting origin is not a supported origin. Reported by Barak Tawily.
  (bug fix)

2.10.2 - February 21, 2019
--------------------------

Added
~~~~~

* Add support for various new SSL / TLS related config options (``ssl_keyfile``, ``ssl_certfile``,
  ``ssl_ca_certs``, ``ssl_certfile``, ``authentication_mechanism``) to the ``messaging`` section in
  ``st2.conf`` config file.

  With those config options, user can configure things such as client based certificate
  authentication, client side verification of a server certificate against a specific CA bundle, etc.

  NOTE: Those options are only supported when using a default and officially supported AMQP backend
  with RabbitMQ server. (new feature) #4541
* Add metrics instrumentation to the ``st2notifier`` service. For the available / exposed metrics,
  please refer to https://docs.stackstorm.com/reference/metrics.html. (improvement) #4536

Changed
~~~~~~~

* Update logging code so we exclude log messages with log level ``AUDIT`` from a default service
  log file (e.g. ``st2api.log``). Log messages with level ``AUDIT`` are already logged in a
  dedicated service audit log file (e.g. ``st2api.audit.log``) so there is no need for them to also
  be duplicated and included in regular service log file.

  NOTE: To aid with debugging, audit log messages are also included in a regular log file when log
  level is set to ``DEBUG`` or ``system.debug`` config option is set to ``True``.

  Reported by Nick Maludy. (improvement) #4538 #4502
* Update ``pyyaml`` dependency to the latest version. This latest version fixes an issue which
  could result in a code execution vulnerability if code uses ``yaml.load`` in an unsafe manner
  on untrusted input.

  NOTE: StackStorm platform itself is not affected, because we already used ``yaml.safe_load``
  everywhere.

  Only custom packs which use ``yaml.load`` with non trusted user input could potentially be
  affected. (improvement) #4510 #4552 #4554
* Update Orquesta to ``v0.4``. #4551

Fixed
~~~~~

* Fixed the ``packs.pack_install`` / ``!pack install {{ packs }}`` action-alias to not have
  redundant patterns. Previously this prevented it from being executed via
  ``st2 action-alias execute 'pack install xxx'``. #4511

  Contributed by Nick Maludy (Encore Technologies)
* Fix datastore value encryption and make sure it also works correctly for unicode (non-ascii)
  values.

  Reported by @dswebbthg, @nickbaum. (bug fix) #4513 #4527 #4528
* Fix a bug with action positional parameter serialization used in local and remote script runner
  not working correctly with non-ascii (unicode) values.

  This would prevent actions such as ``core.sendmail`` which utilize positional parameters from
  working correctly when a unicode value was provided.

  Reported by @johandahlberg (bug fix) #4533
* Fix ``core.sendmail`` action so it specifies ``charset=UTF-8`` in the ``Content-Type`` email
  header. This way it works correctly when an email subject and / or body contains unicode data.

  Reported by @johandahlberg (bug fix) #4533 4534

* Fix CLI ``st2 apikey load`` not being idempotent and API endpoint ``/api/v1/apikeys`` not
  honoring desired ``ID`` for the new record creation. #4542
* Moved the lock from concurrency policies into the scheduler to fix a race condition when there
  are multiple scheduler instances scheduling execution for action with concurrency policies.
  #4481 (bug fix)
* Add retries to scheduler to handle temporary hiccup in DB connection. Refactor scheduler
  service to return proper exit code when there is a failure. #4539 (bug fix)
* Update service setup code so we always ignore ``kombu`` library ``heartbeat_tick`` debug log
  messages.

  Previously if ``DEBUG`` log level was set in service logging config file, but ``--debug``
  service CLI flag / ``system.debug = True`` config option was not used, those messages were
  still logged which caused a lot of noise which made actual useful log messages hard to find.
  (improvement) #4557

2.10.1 - December 19, 2018
--------------------------

Fixed
~~~~~

* Fix an issue with ``GET /v1/keys`` API endpoint not correctly handling ``?scope=all`` and
  ``?user=<username>`` query filter parameter inside the open-source edition. This would allow
  user A to retrieve datastore values from user B and similar.

  NOTE: Enterprise edition with RBAC was not affected, because in RBAC version, correct check is
  in place which only allows users with an admin role to use ``?scope=all`` and retrieve / view
  datastore values for arbitrary system users. (security issue bug fix)

2.10.0 - December 13, 2018
--------------------------

Added
~~~~~

* Added ``notify`` runner parameter to Orquesta that allows user to specify which task(s) to get
  notified on completion.
* Add support for task delay in Orquesta workflows. #4459 (new feature)
* Add support for task with items in Orquesta workflows. #4400 (new feature)
* Add support for workflow output on error in Orquesta workflows. #4436 (new feature)
* Added ``-o`` and ``-m`` CLI options to ``st2-self-check`` script, to skip Orquesta and/or Mistral
  tests. #4347
* Allow user to specify new ``database.authentication_mechanism`` config option in
  ``/etc/st2/st2.conf``.

  By default, SCRAM-SHA-1 is used with MongoDB 3.0 and later and MONGODB-CR (MongoDB Challenge
  Response protocol) for older servers.

  Contributed by @aduca85 #4373
* Add new ``metadata_file`` attribute to the following models: Action, Action Alias, Rule, Sensor,
  TriggerType. Value of this attribute points to a metadata file for a specific resource (YAML file
  which contains actual resource definition). Path is relative to the pack directory (e.g.
  ``actions/my_action1.meta.yaml``, ``aliases/my_alias.yaml``, ``sensors/my_sensor.yaml``,
  ``rules/my_rule.yaml``, ``triggers/my_trigger.yaml`` etc.).

  Keep in mind that triggers can be registered in two ways - either via sensor definition file in
  ``sensors/`` directory or via trigger definition file in ``triggers/`` directory. If
  ``metadata_file`` attribute on TriggerTypeDB model points to ``sensors/`` directory it means that
  trigger is registered via sensor definition. (new feature) #4445
* Add new ``st2client.executions.get_children`` method for returning children execution objects for
  a specific (parent) execution. (new feature) #4444

  Contributed by Tristan Struthers (@trstruth).
* Allow user to run a subset of pack tests by utilizing the new ``-f`` command line option in the
  ``st2-run-pack-tests`` script.

  For example:

  1. Run all tests in a test file (module):

     st2-run-pack-tests -j -x -p contrib/packs/ -f test_action_download

  2. Run a single test class

     st2-run-pack-tests -j -x -p contrib/packs/ -f test_action_download:DownloadGitRepoActionTestCase

  3. Run a single test class method

     st2-run-pack-tests -j -x -p contrib/packs/ -f test_action_download:DownloadGitRepoActionTestCase.test_run_pack_download

  (new feature) #4464

Changed
~~~~~~~

* Redesigned and rewritten the action execution scheduler. Requested executions are put in a
  persistent queue for scheduler to process. Architecture is put into place for more complex
  execution scheduling. Action execution can be delayed on request. (improvement)
* ``core.http`` action now supports additional HTTP methods: OPTIONS, TRACE, PATCH, PURGE.

  Contributed by @emptywee (improvement) #4379
* Runner loading code has been updated so it utilizes new "runner as Python package" functionality
  which has been introduced in a previous release. This means that the runner loading is now fully
  automatic and dynamic.

  All the available / installed runners are automatically loaded and registering on each StackStorm
  service startup.

  This means that ``st2ctl reload --register-runners`` flag is now obsolete because runners are
  automatically registered on service start up. In addition to that,
  ``content.system_runners_base_path`` and ``content.runners_base_paths`` config options are now
  also deprecated and unused.

  For users who wish to develop and user custom action runners, they simply need to ensure they are
  packaged as Python packages and available / installed in StackStorm virtual environment
  (``/opt/stackstorm/st2``). (improvement) #4217
* Old runner names which have been deprecated in StackStorm v0.9.0 have been removed (run-local,
  run-local-script, run-remote, run-remote-script, run-python, http-runner). If you are still using
  actions which reference runners using old names, you need to update them to keep it working.
  #4217
* Update various CLI commands to only retrieve attributes which are displayed in the CLI from the
  API (``st2 execution list``, ``st2 execution get``, ``st2 action list``, ``st2 rule list``,
  ``st2 sensor list``). This speeds up run-time and means now those commands now finish faster.

  If user wants to retrieve and view all the attributes, they can use ``--attr all`` CLI command
  argument (same as before). (improvement) #4396
* Update various internal dependencies to latest stable versions (greenlet, pymongo, pytz,
  stevedore, tooz). #4410

* Improve ``st2.conf`` migration for the new services by using prod-friendly logging settings by default #4415
* Refactor Orquesta workflow to output on error. Depends on PR
  https://github.com/StackStorm/orquesta/pull/101 and https://github.com/StackStorm/orquesta/pull/102
  (improvement)
* Rename ``st2client.liveactions`` to ``st2client.executions``. ``st2client.liveactions`` already
  represented operations on execution objects, but it was incorrectly named.

  For backward compatibility reasons, ``st2client.liveactions`` will stay as an alias for
  ``st2client.executions`` and continue to work until it's fully removed in a future release.

Fixed
~~~~~

* ``st2 login`` CLI commands now exits with non zero exit code when login fails due to invalid
  credentials. (improvement) #4338
* Fix ``st2 key load`` that errors when importing an empty file #43
* Fixed warning in ``st2-run-pack-tests`` about invalid format for ``pip list``. (bug fix)

  Contributed by Nick Maludy (Encore Technologies). #4380
* Fix a bug with ``st2 execution get`` / ``st2 run`` CLI command throwing an exception if the
  result field contained a double backslash string which looked like an unicode escape sequence.
  CLI incorrectly tried to parse that string as unicode escape sequence.

  Reported by James E. King III @jeking3 (bug fix) #4407
* Fix a bug so ``timersengine`` config section in ``st2.conf`` has precedence over ``timer``
  section if explicitly specified in the config file.

  Also fix a bug with default config values for ``timer`` section being used if user only
  specified ``timersengine`` section in the config. Previously user options were incorrectly
  ignored in favor of the default values. (bug fix) #4424
* ``st2 pack install -j`` now only spits JSON output. Similarly, ``st2 pack install -y`` only spits
  YAML output. This change would enable the output to be parsed by tools.
  The behavior of ``st2 pack install`` hasn't changed and is human friendly. If you want to get meta
  information about the pack as JSON (count of actions, sensors etc), you should rely on already
  existing ``st2 pack show -j``.

  Reported by Nick Maludy (improvement) #4260
* Fix string operations on unicode data in Orquesta workflows, associated with PR
  https://github.com/StackStorm/orquesta/pull/98. (bug fix)
* Fix access to st2 and action context in Orquesta workflows, associated with PR
  https://github.com/StackStorm/orquesta/pull/104. (bug fix)
* ``st2ctl reload --register-aliases`` and ``st2ctl reload --register-all`` now spits a warning when
  trying to register aliases with no corresponding action registered in the db.

  Reported by nzlosh (improvement) #4372.

2.9.1 - October 03, 2018
------------------------

Changed
~~~~~~~

* Speed up pack registration through the ``/v1/packs/register`` API endpoint. (improvement) #4342
* Triggertypes API now sorts by trigger ref by default. ``st2 trigger list`` will now show a sorted
  list. (#4348)
* Update ``st2-self-check`` script to include per-test timing information. (improvement) #4359

Fixed
~~~~~

* Update ``st2sensorcontainer`` service to throw if user wants to run a sensor from a pack which is
  using Python 3 virtual environment.

  We only support running Python runner actions from packs which use mixed Python environments
  (StackStorm components are running under Python 2 and particular a pack virtual environment is
  using Python 3). #4354
* Update ``st2-pack-install`` and ``st2 pack install`` command so it works with local git repos
  (``file://<path to local git repo>``) which are in a detached head state (e.g. specific revision
  is checked out). (improvement) #4366
* Fix a race which occurs when there are multiple concurrent requests to resume a workflow. #4369

2.9.0 - September 16, 2018
--------------------------

Added
~~~~~

* Add new runners: ``winrm-cmd``, ``winrm-ps-cmd`` and ``winrm-ps-script``.
  The ``winrm-cmd`` runner executes Command Prompt commands remotely on Windows hosts using the
  WinRM protocol. The ``winrm-ps-cmd`` and ``winrm-ps-script`` runners execute PowerShell commands
  and scripts on remote Windows hosts using the WinRM protocol.

  To accompany these new runners, there are two new actions ``core.winrm_cmd`` that executes remote
  Command Prompt commands along with ``core.winrm_ps_cmd`` that executes remote PowerShell commands.
  (new feature) #1636

  Contributed by Nick Maludy (Encore Technologies).
* Add new ``?tags``, query param filter to the ``/v1/actions`` API endpoint. This query parameter
  allows users to filter out actions based on the tag name . By default, when no filter values are
  provided, all actions are returned. (new feature) #4219
* Add a new standalone standalone ``st2-pack-install`` CLI command. This command installs a pack
  (and sets up the pack virtual environment) on the server where it runs. It doesn't register the
  content. It only depends on the Python, git and pip binary and ``st2common`` Python package to be
  installed on the system where it runs. It doesn't depend on the database (MongoDB) and message
  bus (RabbitMQ).

  It's primary meant to be used in scenarios where the content (packs) are baked into the base
  container / VM image which is deployed to the cluster.

  Keep in mind that the content itself still needs to be registered with StackStorm at some later
  point when access to RabbitMQ and MongoDB is available by running
  ``st2ctl reload --register-all``. (new feature) #3912 #4256
* Add new ``/v1/stream/executions/<id>/output[?output_type=all|stdout|stderr]`` stream API
  endpoint.

  This API endpoint returns event source compatible response format.

  For running executions it returns any output produced so far and any new output as it's produced.
  Once the execution finishes, the connection is automatically closed.

  For completed executions it returns all the output produced by the execution. (new feature)
* Add new ``core.inject_trigger`` action for injecting a trigger instance into the system.

  Keep in mind that the trigger which is to be injected must be registered and exist in the system.
  (new feature) #4231 #4259
* Add support for ``?include_attributes`` query param filter to all the content pack resource
  get all (list) API endpoints (actions, rules, trigger, executions, etc.). With this query
  parameter user can control which API model attributes (fields) to receive in the response. In
  situations where user is only interested in a subset of the model attributes, this allows for a
  significantly reduced response size and for a better performance. (new feature) (improvement)
  #4300
* Add new ``action_sensor.emit_when`` config option which allows user to specify action status for
  which actiontrigger is emitted. For backward compatibility reasons it defaults to all the action
  completed states. (improvement) #4312 #4315

  Contributed by Shu Sugimoto.
* Improve performance of schedule action execution (``POST /v1/executions``) API endpoint.

  Performance was improved by reducing the number of duplicated database queries, using atomic
  partial document updates instead of full document updates and by improving database document
  serialization and de-serialization performance. (improvement) #4030 #4331
* Ported existing YAQL and Jinja functions from st2common to Orquesta. (new feature)
* Add error entry in Orquesta workflow result on action execution failure. (improvement)

Changed
~~~~~~~

* ``st2 key list`` command now defaults to ``--scope=all`` aka displaying all the datastore values
  (system and current user scoped) . If you only want to display system scoped values (old behavior)
  you can do that by passing ``--scope=system`` argument to the ``st2 key list`` command
  (``st2 key list --scope=system``). (improvement) #4221
* The orquesta conductor implemented event based state machines to manage state transition of
  workflow execution. Interfaces to set workflow state and update task on action execution
  completion have changed and calls to those interfaces are changed accordingly. (improvement)
* Change ``GET /v1/executions/<id>/output`` API endpoint so it never blocks and returns data
  produced so far for running executions. Behavior for completed executions is the same and didn't
  change - all data produced by the execution is returned in the raw format.

  The streaming (block until execution has finished for running executions) behavior has been moved
  to the new ``/stream/v1/executions/<id>/output`` API endpoint.

  This way we are not mixing non-streaming (short lived) and streaming (long lived) connections
  inside a single service (st2api). (improvement)
* Upgrade ``mongoengine`` (0.15.3) and ``pymongo`` (3.7.1) to the latest stable version. Those
  changes will allow us to support MongoDB 3.6 in the near future.

  New version of ``mongoengine`` should also offer better performance when inserting and updating
  larger database objects (e.g. executions). (improvement) #4292
* Trigger parameters and payload schema validation is now enabled by default
  (``system.validate_trigger_parameters`` and ``system.validate_trigger_payload`` config options
  now default to ``True``).

  This means that trigger parameters are now validated against the ``parameters_schema`` defined on
  the trigger type when creating a rule and trigger payload is validated against ``payload_schema``
  when dispatching a trigger via the sensor or via the webhooks API endpoint.

  This provides a much safer and user-friendly default value. Previously we didn't validate trigger
  payload for custom (non-system) triggers when dispatching a trigger via webhook which meant that
  webhooks API endpoint would silently accept an invalid trigger (e.g. referenced trigger doesn't
  exist in the database or the payload doesn't validate against the ``payload_schema``), but
  ``TriggerInstanceDB`` object would never be created because creation failed inside the
  ``st2rulesengine`` service. This would make such issues very hard to troubleshoot because only
  way to find out about this failure would be to inspect the ``st2rulesengine`` service logs.
  (improvement) #4231
* Improve code metric instrumentation and instrument code and various services with more metrics.
  Also document various exposed metrics. Documentation can be found at
  https://docs.stackstorm.com/latest/reference/metrics.html (improvement) #4310
* Add new ``metrics.prefix`` config option. With this option user can specify an optional prefix
  which is prepended to each metric key (name). This comes handy in scenarios where user wants to
  submit metrics from multiple environments / deployments (e.g. testing, staging, dev) to the same
  backend instance. (improvement) #4310
* Improve ``st2 execution tail`` CLI command so it also supports Orquesta workflows and arbitrarily
  nested workflows. Also fix the command so it doesn't include data from other unrelated running
  executions. (improvement) #4328
* Change default NGINX configuration to use HTTP 308 redirect, rather than 301, for plaintext requests.
  #4335
* Improve performance of the ``GET /v1/actions/views/overview`` API endpoint. (improvement) #4337

Fixed
~~~~~

* Fix an issue with ``AttributeError: module 'enum' has no attribute 'IntFlag'`` error which would
  appear when using Python 3 for a particular pack virtual environment and running on RHEL /
  CentOS. (bug fix) #4297
* Fix a bug with action runner throwing an exception and failing to run an action if there was an
  empty pack config inside ``/opt/stackstorm/configs/``. (bug fix) #4325
* Fix ``action_sensor.enable`` config option so it works correctly if user sets this option to a
  non-default value of ``True``. (bug fix) #4312 #4315

  Contributed by Shu Sugimoto.
* Update ``GET /v1/actions/views/entry_point/<action ref>`` to return correct ``Content-Type``
  response header based on the entry point type / file extension. Previously it would always
  incorrectly return ``application/json``. (improvement) #4327

Deprecated
~~~~~~~~~~

* The CloudSlang runner is now deprecated. In StackStorm 3.1 it will be removed from the core
  StackStorm codebase. The runner code will be moved to a separate repository, and no longer
  maintained by the core StackStorm team. Users will still be able to install and use this runner,
  but it will require additional steps to install.
* The ``winexe``-based Windows runners are now deprecated. They will be removed in StackStorm 3.1.
  They have been replaced by ``pywinrm``-based Windows runners. See
  https://docs.stackstorm.com/latest/reference/runners.html#winrm-command-runner-winrm-cmd
  for more on using these new runners.

2.8.1 - July 18, 2018
---------------------

Added
~~~~~

* Update ``st2`` CLI to inspect ``COLUMNS`` environment variable first when determining the
  terminal size. Previously this environment variable was checked second last (after trying to
  retrieve terminal size using various OS specific methods and before falling back to the default
  value).

  This approach is more performant and allows user to easily overwrite the default value or value
  returned by the operating system checks - e.g. by running ``COLUMNS=200 st2 action list``.
  (improvement) #4242

Changed
~~~~~~~

* Update ``st2client/setup.py`` file to dynamically load requirements from
  ``st2client/requirements.txt`` file. The code works with pip >= 6.0.0, although using pip 9.0.0
  or higher is strongly recommended. (improvement) #4209
* Migrated runners to using the ``in-requirements.txt`` pattern for "components" in the build
  system, so the ``Makefile`` correctly generates and installs runner dependencies during
  testing and packaging. (improvement) (bugfix) #4169

  Contributed by Nick Maludy (Encore Technologies).
* Update ``st2`` CLI to use a more sensible default terminal size for table formatting purposes if
  we are unable to retrieve terminal size using various system-specific approaches.

  Previously we would fall back to a very unfriendly default of 20 columns for a total terminal
  width. This would cause every table column to wrap and make output impossible / hard to read.
  (improvement) #4242

Fixed
~~~~~

* Fixed a bug where ``secret: true`` was not applying to full object and array trees. (bugfix) #4234
  Reported by @jjm

  Contributed by Nick Maludy (Encore Technologies).
* Mark ``password`` ``http-request`` parameter as a secret. (bug fix) #4245

  Reported by @daniel-mckenna

2.8.0 - July 10, 2018
---------------------

Added
~~~~~

* Orquesta - new StackStorm-native workflow engine. This is currently in **beta**. (new feature)
* Added metrics for collecting performance and health information about the various ST2 services
  and functions. (new feature) #4004 #2974
* When running a dev (unstable) release include git revision hash in the output when using
  ``st2 --version`` CLI command. (new feature) #4117
* Update rules engine to also create rule enforcement object when trigger instances fails to match
  a rule during the rule matching / filtering phase due to an exception in the rule criteria (e.g.
  invalid Jinja expression, etc.).

  This change increases visibility into rules which didn't match due to an exception. Previously
  this was only visible / reflected in the rules engine log file. (improvement) #4134
* Add new ``GET /v1/ruleenforcements/views[/<enforcement id>]`` API endpoints which allow user to
  retrieve RuleEnforcement objects with the corresponding TriggerInstance and Execution objects.
  (new feature) #4134
* Add new ``status`` field to the ``RuleEnforcement`` model. This field can contain the following
  values - ``succeeded`` (trigger instance matched a rule and action execution was triggered
  successfully), ``failed`` (trigger instance matched a rule, but it didn't result in an action
  execution due to Jinja rendering failure or other exception). (improvement) #4134 #4152
* Add trigger type reference based filtering to the ``/v1/triggerinstances`` API endpoint - e.g.
  ``/v1/triggerinstances?trigger_type=core.st2.webhook``. (new feature) #4151
* Add new ``--python3`` flag to ``st2 pack install`` CLI command and ``python3`` parameter to
  ``packs.{install,setup_virtualenv}`` actions. When the value of this parameter is True, it
  uses ``python3`` binary when creating virtual environment for that pack (based on the value of
  ``actionrunner.python3_binary`` config option).

  Note 1: For this feature to work, Python 3 needs to be installed on the system, ``virtualenv``
  package installed on the system needs to support Python 3 (it needs to be a recent version) and
  pack in question needs to support Python 3.

  Note 2: This feature is experimental and opt-in. (new feature) #4016 #3922 #4149
* Add two new Jinja filters - ``basename`` (``os.path.basename``) and ``dirname``
  (``os.path.dirname``). #4184

  Contributed by Florian Reisinger (@reisingerf).

Changed
~~~~~~~

* Update st2 CLI to create the configuration directory and file, and authentication tokens with
  secure permissions (eg: readable only to owner) #4173
* Refactor the callback module for the post run in runner to be more generic. (improvement)
* Update various Python dependencies to the latest stable versions (gunicorn, gitpython,
  python-gnupg, tooz, flex). #4110
* Update all the service and script entry points to use ``/etc/st2/st2.conf`` as a default value
  for the config file location.

  This way users don't need to explicitly provide ``--config-file`` CLI argument when running
  various scripts (e.g. ``st2-track-result``, ``st2-apply-rbac-definitions``, etc.) and when they
  just want to use a default config file. (improvement) #4111
* Update st2 CLI to print a warning if a non-unicode system locale which would prevent StackStorm
  to function correctly in some scenarios is used. (improvement) #4127 #4120
* Upgrade various internal Python library dependencies to the latest stable versions (kombu, amqp,
  gitpython, pytz, semver, oslo.utils). (improvement) #4162
* Move from ``keyczar`` library to ``cryptography`` library for handling symmetric encryption and
  decryption (secret datastore values).

  Note: This change is fully backward compatible since it just changes the underlying backend and
  implementation details. The same underlying encryption algorithm is used (AES256 in CBC mode
  with HMAC signature). (improvement) #4165

Fixed
~~~~~

* Fixed a bug where secrets in pack configs weren't being masked. Recently we
  introduced support for nested objects and arrays. Secret parameters within these
  nested objects and arrays were not being masked. The fix involves us fully
  traversing deeply nested objects and arrays and masking out any variables
  marked as secret. This means we now support pack config JSON schemas with
  ``type: object`` and its corresponding ``parameters: {}`` stanza, along with
  ``type: array`` and its corresponding ``items: {}`` stanza. We still do NOT
  support JSON schema combinations that includes the ``anyOf``, ``allOf``,
  ``oneOf``, and ``not`` keywords. (bug fix) #4139

  Contributed by Nick Maludy (Encore Technologies).
* Style clean up to transport queues module and various config modules. (improvement)
* Fixed CLI help for ``st2 action-alias match`` and ``execute``. (#4174).
* Fix regression in ``?include_attributes`` query param filter in the ``/v1/executions`` API
  endpoint. (bug fix) #4226

2.7.2 - May 16, 2018
--------------------

Changed
~~~~~~~

* Reduce load on LDAP server and cache user groups response in an in-memory cache when RBAC
  remote LDAP group to local RBAC role synchronization feature is enabled.

  Previously on authentication the code would hit LDAP server multiple times to retrieve user
  groups. With this change, user LDAP groups are only retrieved once upon authentication and
  cached and re-used in-memory by default for 120 seconds.

  This reduces load on LDAP server and improves performance upon regular and concurrent user
  authentication.

  This functionality can be disabled by setting ``cache_user_groups_response`` LDAP
  authentication backend kwarg to ``false``.

  Note: This change only affects users which utilize RBAC with remote LDAP groups to local RBAC
  roles synchronization feature enabled. (enterprise) (bug fix) #4103 #4105

Fixed
~~~~~

* Fix an issue (race condition) which would result in not all the remote LDAP groups being
  synchronized with local RBAC roles if a user tried to authenticate with the same auth token
  concurrently in a short time frame.

  Note: This issue only affects users which utilize RBAC with remote LDAP groups to local RBAC
  roles synchronization feature enabled. (enterprise) (bug fix) #4103 #4105
* Fix an issue with some sensors which rely on ``select.poll()`` (FileWatch, GithubSensor, etc.)
  stopped working with StackStorm >= 2.7.0.

  StackStorm v2.7.0 inadvertently introduced a change which broke a small set of sensors which
  rely on ``select.poll()`` functionality. (bug fix) #4118

* Throw if ``id`` CLI argument is not passed to the ``st2-track-result`` script. (bug fix) #4115
* Fixed pack config's not properly rendering Jinja expressions within lists. (bugfix) #4121

  Contributed by Nick Maludy (Encore Technologies).
* Fixed pack config rendering error throw meaningful message when a Jinja syntax error is
  encountered. (bugfix) #4123

  Contributed by Nick Maludy (Encore Technologies).

2.7.1 - April 20, 2018
----------------------

Changed
~~~~~~~

* When creating a pack environment during the pack installation, we now pass ``--no-download`` flag
  to the ``virtualenv`` binary. This way version of pip, wheel and distutils which is enforced by
  virtualenv is used instead of downloading the latest stable versions from PyPi.

  This results in more reproducible pack virtual environments and we also ensure pip 9.0 is used (
  there are some known issues with pip 10.0).

  If for some reason you want to revert to the old behavior, you can do that by passing
  ``no_download=False`` parameter to the ``packs.setup_virtualenv`` action. #4085

Fixed
~~~~~

* Fix ``st2 pack search`` and ``POST /api/v1/packs/index/search`` API endpoint so it doesn't
  return internal server error when a single pack search term is provided. (bug fix) #4083

2.7.0 - April 12, 2018
----------------------

Added
~~~~~

* Update ``st2 execution tail`` command so it supports double nested workflows (workflow ->
  workflow -> execution). Previously, only top-level executions and single nested workflows
  (workflow -> execution) were supported. (improvement) #3962 #3960
* Add support for utf-8 / unicode characters in the pack config files. (improvement) #3980 #3989

  Contributed by @sumkire.
* Added the ability of ``st2ctl`` to utilize environment variables from ``/etc/default/st2ctl``
  (for Ubuntu/Debian) and ``/etc/sysconfig/st2ctl`` (RHEL/CentOS). This allows
  deployments to override ``COMPONENTS`` and ``ST2_CONF`` in a global location
  so ``st2ctl`` can start/stop/restart selected components and utilize a non-default
  location for ``st2.conf``.
  (new feature) #4027

  Contributed by Nick Maludy (Encore Technologies).
* Add support for new optional ``content_version`` runner parameter to the Python and Local Shell
  Script runner. This parameter can contain a git commit hash / tag / branch from a pack git
  repository and runner will ensure this revision of the pack content (Python action / local shell
  script action) is used for a particular action execution.

  Keep in mind that providing this parameter only ensures a particular revision of the pack content
  is used. Python runner virtual environment and dependencies are outside of this scope.

  Note: To be able to utilize this functionality, git version >= 2.5.0 must be installed on the
  system.
  (new feature) #3997
* Update windows runner to correctly handle and use ``timeout`` action execution status.
  (improvement) #4047
* Add missing ``scope``, ``decrypt`` and ``encrypt`` arguments to the datastore management
  related methods on the SensorService class. (improvement) #3895 #4057 #4058

  Reported by @djh2020, @mxmader.
* Add context field to rule model in which each rule has its own corresponding user. Besides, there
  is a new RBAC configuration ``permission_isolation``. Whoever can only operate and observe their
  own rules or executions except ``system_user`` and users with RBAC admin role when set to
  ``True``. That means system_user has the most powerful permission to operate all resources
  including rules or executions. (new feature) #4013

  Contributed by Hanxi Liu (@apolloliu).

Changed
~~~~~~~

* Modified RabbitMQ connection error message to make clear that it is an MQ connection issue. #3992
* Additional refactor which makes action runners fully standalone and re-distributable Python
  packages. Also add support for multiple runners (runner modules) inside a single Python package
  and consolidate Python packages from two to one for the following runners: local runners, remote
  runners, windows runners. (improvement) #3999
* Upgrade eventlet library to the latest stable version (0.22.1) (improvement) #4007 #3968
* Increase maximum retry delay for ``action.retry`` policy from 5 seconds to 120 seconds. Because
  of the way retries are currently implemented (they are not st2notifier service restart safe),
  long retry delays are not recommended. For more information on this limitation please refer to
  the documentation - https://docs.stackstorm.com/reference/policies.html#retry. #3630 #3637
* Update Python runner so it throws a more user-friendly exception in case Python script tries to
  access a key in ``self.config`` dictionary which doesn't exist. (improvement) #4014
* Update various Python dependencies to the latest stable versions (apscheduler, gitpython,
  pymongo, stevedore, paramiko, tooz, flex, webob, prance).
* Refactored mistral runner to support callback from mistral instead of relying on st2resultstracker.
  This reduces the unnecessary traffic and CPU time by querying the mistral API. Included a command to
  manually add a state entry for Mistral workflow execution to recover from any callback failures.
  (improvement)
* Throw a more user-friendly error when writing pack data files to disk and when an invalid file
  path is provided (e.g. path is outside the pack directory, etc.). (improvement) #4039 #4046
* Change the output object returned by Windows runners so it matches the format from the local and
  remote runner.

  Note: This change is backward incompatible - ``result`` attribute has been removed (same
  information is available in ``stdout`` attribute), ``exit_code`` renamed to ``return_code`` and
  two new attributes added - ``succeeded`` and ``failed``.

  For more information, please refer to the upgrade notes. #4044 #4047

Fixed
~~~~~

* Fix Python runner actions and ``Argument list too long`` error when very large parameters are
  passed into the action. The fix utilizes ``stdin`` to pass parameters to the Python action wrapper
  process instead of CLI argument list. (bug fix) #1598 #3976
* Fix a regression in ``POST /v1/webhooks/<webhook name>`` API endpoint introduced in v2.4.0
  and add back support for arrays. In 2.4.0 support for arrays was inadvertently removed and
  only objects were supported. Keep in mind that this only applies to custom user-defined
  webhooks and system ``st2`` webhook still requires input to be an object (dictionary).
  (bug fix) #3956 #3955
* Fix a bug in the CLI causing ``st2 execution pause`` and ``st2 execution resume``
  to not work. (bugfix) #4001

  Contributed by Nick Maludy (Encore Technologies).
* Fixed missing "paused" status option from "st2 execution list" help output. (bugfix) #4037

  Contributed by Ben Hohnke (NTT Communications ICT Solutions)
* Fix "st2 pack install" command so it doesn't require access to pack index (index.stackstorm.org)
  when installing a local pack (pack name starting with "file://"). (bug fix) #3771 #3772
* Fix rules engine so it correctly handles and renders action parameters which contain Jinja
  expressions and default values. (bug fix) #4050 #4050

  Reported by @rakeshrm.
* Make sure ``observer`` system role also grants ``pack_search`` permission. (bug fix) #4063 #4064

  Reported by @SURAJTHEGREAT.
* Fix st2 webhook get -h which was asking for a name or id as opposed to the URL of the webhook.
  Also, fix st2 webhook list to explicitly add a webhook column. (bugfix) #4048
* Fix an issue with pack config validation code throwing a non-user friendly error message in case
  config item of type array failed config schema validation. (bug fix) #4166 #4168

  Reported by @NikosVlagoidis.

2.6.0 - January 19, 2018
------------------------

Added
~~~~~

* Add new ``get_user_info`` method to action and sensor service. With this method, user can
  retrieve information about the user account which is used to perform datastore operations inside
  the action and sensor service. (new feature) #3831
* Add new ``/api/v1/user`` API endpoint. This API endpoint is only available to the authenticated
  users and returns various metadata on the authenticated user (which method did the user use to
  authenticate, under which username the user is authenticated, which RBAC roles are assignment to
  this user in case RBAC is enabled, etc.) (new feature) #3831
* The ``/api/v1/match_and_execute`` API endpoint matches a single alias and executes multiple times
  if the alias format has a ``match_multiple`` key set to ``true``. Please refer to the
  documentation for usage. #3884

  Contributed by @ahubl-mz.
* Add ability to share common code between python sensors and python actions. You can now place
  common code inside a ``lib`` directory inside a pack (with an ``__init__.py`` inside ``lib``
  directory to declare it a python package). You can then import the common code in sensors and
  actions. Please refer to documentation for samples and guidelines. #3490
* Add support for password protected sudo to the local and remote runner. Password can be provided
  via the new ``sudo_password`` runner parameter. (new feature) #3867
* Add new ``--tail`` flag to the ``st2 run`` / ``st2 action execute`` and ``st2 execution re-run``
  CLI command. When this flag is provided, new execution will automatically be followed and tailed
  after it has been scheduled. (new feature) #3867
* Added flag ``--auto-dict`` to ``st2 run`` and ``st2 execution re-run`` commands. This flag must now
  be specified in order to automatically convert list items to dicts based on presence of colon
  (``:``) in all of the list items (new feature) #3909
* Allow user to set default log level used by all the Python runner actions by setting
  ``actionrunner.pythonrunner```` option in ``st2.conf`` (new feature) #3929
* Update ``st2client`` package which is also utilized by the CLI so it also works under Python 3.

  Note: Python 2.7 is only officially supported and tested Python version. Using Python 3 is at
  your own risk - they are likely still many bugs related to Python 3 compatibility. You have been warned.
  (new feature) #3929 #3932

  Contributed by Anthony Shaw.
* Add ``?limit=-1`` support for the API to fetch full result set (CLI equivalent flag
  ``--last/-n``). Post error message for ``limit=0`` and fix corner case where negative values for
  limit query param were not handled correctly. #3761 #3708 #3735
* Only allow RBAC admins to retrieve all the results at once using ``?limit=-1`` query param, upate
  the code so ``api.max_page_size`` config option only applies to non-admin users, meaning users
  with admin permission can specify arbitrary value for ``?limit`` query param which can also be
  larger than ``api.max_page_size``. (improvement) #3939
* Add new ``?include_attributes`` query param filter to ``/v1/executions/`` API endpoint
  With this filter user can select which fields to include in the response (whitelist approach,
  opposite of the existing ``?exclude_attributes`` filter).

  For example, if you only want to retrieve ``id`` and ``status`` field, the URL would look like
  this - ``/v1/executions?include_attributes=id,status``. (new feature) #3953 #3858 #3856

Changed
~~~~~~~

* ``st2actions.runners.pythonrunner.Action`` class path for base Python runner actions has been
  deprecated since StackStorm v1.6.0 and will be fully removed in StackStorm v2.7.0. If you have
  any actions still using this path you are encouraged to update them to use
  ``st2common.runners.base_action.Action`` path. #3803
* Refactor ``st2common`` Python package so it's fully self sustaining and can be used in a
  standalone manner. (improvement) #3803
* Refactor Python action runner so it only depends on ``st2common`` Python package (previously it
  also depended on ``st2actions``) and can be used in a standalone mode. Previously pack config and
  and some other parameters were retrieved inside the Python process wrapper, but now they are
  retrieved inside the runner container and passed to the runner. This also makes it easier to add
  support for pack configs to other runners in the future. (improvement) #3803
* Update various Python dependencies to the latest stable versions (kombu, amqp, apscheduler,
  gitpython, pymongo, stevedore, paramiko, prompt-toolkit, flex). #3830
* Mask values in an Inquiry response displayed to the user that were marked as "secret" in the
  inquiry's response schema. #3825
* Real-time action output streaming is now enabled by default. For more information on this
  feature, please refer to the documentation - https://docs.stackstorm.com/latest/reference/action_output_streaming.html.
  You can disable this functionality by setting ``actionrunner.stream_output`` config option in
  ``st2.conf`` to ``False`` and restart the services (``sudo st2ctl restart``).

Fixed
~~~~~

* Fully fix performance regressions for short Python runner actions introduced in the past and
  partially fixed in #3809. (bug fix) #3803
* Fix 'NameError: name 'cmd' is not defined' error when using ``linux.service`` with CentOS systems.
  #3843. Contributed by @shkadov
* Fix bugs with newlines in execution formatter (client) (bug fix) #3872
* Fixed ``st2ctl status`` to use better match when checking running process status. #3920
* Removed invalid ``st2ctl`` option to re-open Mistral log files. #3920
* Update garbage collection service and ``st2-purge-executions`` CLI tool and make deletion more
  efficient. Previously we incorrectly loaded all the execution fields in memory, but there was no
  need for that and now we only retrieve and load id which is the only field we need. #3936

  Reported by @kevin-vh.

2.5.1 - December 14, 2017
-------------------------

Added
~~~~~

* Add new ``log_level`` runner parameter to Python runner. With this parameter, user can control
  which log messages generated by Python runner actions are output to action ``stderr``. For
  backward compatibility reasons it defaults to ``debug``.
  This functionality comes handy in situations when an action depends on an external library which
  logs a lot of information under ``debug``, but you only want to see messages with log level
  ``error`` or higher (or similar). (new feature) #3824
* Add stevedore related metadata to Python package setup.py files for runner packages. This way
  runners can be installed using pip and dynamically enumerated and loaded using stevedore and
  corresponding helper functions.

  All runners are now also fully fledged Python packages (previously they were single module
  Python packages which caused various install and distribution related issues when installing
  them via pip) (new feature)
* Add new ``search`` rule criteria comparison operator. Please refer to the documentation for
  usage. (new feature) #3833

  Contributed by @ahubl-mz.
* Now a more user-friendly error message is thrown if a cycle is found inside the Jinja template
  string (e.g. when parameter / variable references itself). (improvement) #3908
* Jinja templates in default parameter values now render as live parameters, if no "real" live
  parameter was provided. This allows the template to render pre-schema validation, resulting
  in the intended value type. (improvement) #3892

Changed
~~~~~~~

* Update the output of ``st2 execution {run,get}`` CLI command to colorize the value of the
  ``status`` attribute (green for ``succeeded``, red for ``failed``, etc. aka the same as for the
  output of ``st2 execution list`` command). (improvement) #3810

  Contributed by Nick Maludy (Encore Technologies).
* Update log messages in the datastore service to correctly use ``DEBUG`` log level instead of
  ``AUDIT``. #3845
* Add the ability of ``st2 key load`` to load keys from both JSON and YAML files. Files can now
  contain a single KeyValuePair, or an array of KeyValuePairs. (improvement) #3815
* Add the ability of ``st2 key load`` to load non-string values (objects, arrays, integers,
  booleans) and convert them to JSON before going into the datastore, this conversion requires the
  user passing in the ``-c/--convert`` flag. (improvement) #3815
* Update ``st2 key load`` to load all properties of a key/value pair, now secret values can be
  loaded. (improvement) #3815

  Contributed by Nick Maludy (Encore Technologies).

Fixed
~~~~~

* Fix log messages generated by Python runner actions to include the correct action class name.
  Previously they always incorrectly used "ABCMeta" instead of the actual action class name.
  (bug fix) #3824
* Fix ``st2 execution tail [last]`` CLI command so it doesn't throw an exception if there are no
  executions in the database. (bug fix) #3760 #3802
* Fix edge case for workflows stuck in running state. When Mistral receives a connection error from
  the st2 API on requesting action execution, there's a duplicate action execution stuck in
  requested state. This leads to the st2resultstracker assuming the workflow is still running.
* Fix a regression and a bug with no API validation being performed and API returning 500 instead
  of 400 status code if user didn't include any request payload (body) when hitting POST and PUT
  API endpoints where body is mandatory. (bug fix) #3864
* Fix a bug in Python runner which would cause action log messages to be duplicated in action
  stderr output when utilizing action service / datastore service inside actions. (bug fix)
* Fix performance issue on the CLI when formatting the output as JSON or YAML. (bug fix) #3697

  Contributed by Nick Maludy (Encore Technologies).

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
* Added two new rule operators, ``inside`` and ``ninside`` which allow for the reverse intent of
  the ``contains`` and ``ncontains`` operators. #3781

  Contributed by @lampwins.
* Allow user to use more expressive regular expressions inside action alias format string by
  allowing them to specify start (``^``) and end (``$``) anchors. Previously, those anchors were
  automatically added at the beginning and end of the alias format string. Now they are only added
  if a format string doesn't already contain them. #3789

  Contributed by @ahubl-mz.
* Add new ``POST /v1/aliasexecution/match_and_execute`` API endpoint which allows user to
  schedule an execution based on a command string if a matching alias is found in the database.

  This API endpoint is meant to be used with chat bot plugins. It allows them to be simple thin
  wrappers around this API endpoint which send each chat line to this API endpoint and handle the
  response. #3773
* Add several improvements to the installation scripts: They support using proxy servers.
  ``~stanley`` no longer has to be ``/home/stanley``. In addition to the on-screen display, the
  output from the installation script is now logged to a file beginning with ``st2-install`` under
  ``/var/log/st2/``. Furthermore, the script handles re-runs better, although it's
  not fully idempotent yet. More improvements are expected in the near future.
  st2-packages: #505, #506, #507, #508, #509, #510, #512, #517.

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

* Minor language and style tidy up of help strings and error messages. #3782

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
* Fix ``st2ctl clean`` not using database connection information from config.
  This now uses the new ``st2-cleanup-db`` command. (bug fix) #3659

  Contributed by Nick Maludy (Encore Technologies).

Changed
~~~~~~~

* Update ``st2`` CLI command to print a more user-friendly usage / help string if no arguments are
  passed to the CLI. (improvement) #3710
* Allow user to specify multiple values for a parameter of type array of dicts when using
  ``st2 run`` CLI command. #3670

  Contributed by Hiroyasu OHYAMA.
* Added new command ``st2-cleanup-db`` that drops the current StackStorm MongoDB database. #3659

  Contributed by Nick Maludy (Encore Technologies).

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
* Fix trace list API endpoint sorting by ``start_timestamp``, using ``?sort_desc=True|False`` query
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

* Fix ``st2ctl reload`` command so it preserves exit code from ``st2-register-content`` script and
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
* Add support for ``st2 login`` and ``st2 whoami`` commands. These add some additional functionality
  beyond the existing ``st2 auth`` command and actually works with the local configuration so that
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
  "get all" API endpoint result set (e.g. ``?id=1,2,3,4``). This allows for a better client and
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
* Add missing ``pytz`` dependency to ``st2client`` requirements file. (bug-fix)
* Fix datastore access on Python runner actions (set ``ST2_AUTH_TOKEN`` and ``ST2_API_URL`` env
  variables in Python runner actions to match sensors). (bug-fix)
* Alias names are now correctly scoped to a pack. This means the same name for alias can be used
  across different packs. (bug-fix)
* Fix a regression in filtering rules by pack with CLI. (bug-fix)
* Make sure ``st2-submit-debug-info`` cleans up after itself and deletes a temporary directory it
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

* Fix ``timestamp_lt`` and ``timestamp_gt`` filtering in the ``/executions`` API endpoint. Now we
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
