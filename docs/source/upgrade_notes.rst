Upgrade Notes
=============

|st2| 1.1
---------

* Triggers now have a `ref_count` property which must be included in Trigger objects
  created in previous versions of |st2|. A migration script is shipped in
  ${dist_packages}/st2common/bin/migrate_triggers_to_include_ref_count.py on installation.
  The migration script is run as part of st2_deploy.sh when you upgrade from versions >= 0.13 to
  1.1.
* Messaging queues are now exlusive and in some cases renamed from previous versions. To
  remove old queues run the migration script
  ${dist_packages}/st2common/bin/migrate_messaging_setup.py on installation. The migration
  script is run as part of st2_deploy.sh when you upgrade from versions >= 0.13 to 1.1.
* Mistral moves to YAQL v1.0 and earlier versions of YAQL are deprecated. Expect some minor
  syntax changes to YAQL expressions.
* Mistral has implemented new YAQL functions such as env and task. The ``env()`` function replaces
  ``$.__env`` when referencing environment variables from the data context. Given task1,
  the function call ``task(task1).result``, replaces ``$.task1`` when referencing result of task1.
  ``$.task1`` will still be supported until the next major release of Mistral.

|st2| 0.11
-------------

* Rules now have to be part of a pack. If you don't specify a pack,
  pack name is assumed to be `default`. A migration script
  (migrate_rules_to_include_pack.py) is shipped in ${dist_packages}/st2common/bin/
  on installation. The migration script
  is run as part of st2_deploy.sh when you upgrade from versions < 0.9 to 0.11.

|st2| 0.9
---------

* Process names for all |st2| services now start with "st2". sensor_container now runs as
  st2sensorcontainer, rules_engine runs as st2rulesengine, actionrunner now runs as
  st2actionrunner. st2ctl has been updated to handle the name change seamlessly. If you have tools
  that rely on the old process names, upgrade them to use new names.

* All |st2| tools now use "st2" prefix as well. rule_tester is now st2-rule-tester, registercontent
  is now st2-register-content.

* Authentication is now enabled by default for production (package based) deployments. For
  information on how to configure auth, see http://docs.stackstorm.com/install/deploy.html.

* For consistency reasons, rename existing runners as described below:

  * ``run-local`` -> ``local-shell-cmd``
  * ``run-local-script`` -> ``local-shell-script``
  * ``run-remote`` -> ``remote-shell-cmd``
  * ``run-remote-script`` -> ``remote-shell-script``
  * ``run-python`` -> ``python-script``
  * ``run-http`` -> ``http-request``

  Note: For backward compatibility reasons, those runners are still available
  and can be referenced through their old names, but you are encouraged to
  update your actions to use the new names.
