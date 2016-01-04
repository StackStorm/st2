Upgrade Notes
=============

|st2| In Development
--------------------

* New ``abandoned`` action execution status has been introduced. State is applied to action execution
  when an actionrunner currently running some executions quits or is killed via TERM.This is therefore
  effectively a failure state as |st2| can no longer validate the state of this execution. Being a
  failure state any code that checks for an action failure should be updated to check for ``abandoned``
  state in addition to ``failed`` and ``timeout``.

* ``params`` attribute in the action chain task definition has been replaced with the new
  ``parameters`` attribute. This way it's now consistent with the attribute name in the action
  metadata file. For backward compatibility reason, old parameter name will still be supported
  until the next major release, but you are encouraged to update your action chain definitions
  to use the new parameters name.

|st2| 1.2
---------

* Refactor retries in the Mistral action runner to use exponential backoff. Configuration options
  for Mistral have changed. The options ``max_attempts`` and ``retry_wait`` are deprecated. Please
  refer to the configuration section of docs for more details.
* Change ``headers`` and ``params`` parameters in the ``core.http`` action from ``string`` to
  ``object``. If you have any code or rules which calls this action, you need to update it to
  pass in a new and correct type.
* Local runner has been updated so all the commands which are executed as a different user and
  result in using sudo set ``$HOME`` variable to the home directory of the target user. Previously,
  $HOME variable reflected the home directory of the user which executed sudo and under which
  action runner is running.

  Keep in mind that this condition is only met if action runner is running as root and / or if
  action runner is running a system user (stanley) and a different user is requested when running
  a command using ``user`` parameter.
* Support of default values is added to the API model. As a result, input parameters defined in
  the action metadata that is type of string no longer supports None or null.
* New ``timeout`` action execution status has been introduced. This status is a special type of
  a failure and implies an action timeout.

 All the existing runners (local, remote, python, http, action chain) have been updated to utilize
 this new status when applicable. Previously, if an action timed out, status was set to ``failed``
 and the timeout could only be inferred from the error message in the result object.

 If you have code which checks for an action failure you need to update it to also check for
 ``timeout`` in addition to ``failed`` status.

Upgrading from 1.1
~~~~~~~~~~~~~~~~~~

To upgrade a pre-1.2.0 StackStorm instance provisioned with the :doc:`install/all_in_one`, you will need to perform the following steps:

  1. Back up `/opt/puppet/hieradata/answers.json`.

  2. Update (or insert) the following lines in `/opt/puppet/hieradata/answers.yaml`:

  ```
  st2::version: 1.2.0
  st2::revision: 8
  st2::mistral_git_branch: st2-1.2.0
  hubot::docker: true
  ```

  If `answers.yaml` does not exist, create it. If you changed any install parameters manually (e.g. password, ChatOps token, SSH user), put these values into `answers.yaml` as well, otherwise they'll be overwritten.

  3. If you're running ChatOps, stop the Hubot service with `service hubot stop`.

  4. Remove `/etc/facter/facts.d/st2web_bootstrapped.txt` and execute `update-system`:

  ```
  sudo rm /etc/facter/facts.d/st2web_bootstrapped.txt
  sudo update-system
  ```

  5. After the update is done, restart StackStorm and hubot:

  ```
  sudo st2ctl restart
  sudo service docker-hubot restart
  ```

To verify the upgrade, please follow the link to run the :doc:`self-verification script <troubleshooting/self_verification>`.

|st2| 1.1
---------

Migrating to v1
~~~~~~~~~~~~~~~
The :doc:`install/st2_deploy` will upgrade v0.13 to v1.1. However we encourage to switch to :doc:`install/all_in_one`. To migrate to new All-in-one deployment from the existing pre v1.1 installations:

    1. Install |st2| on a new clean box with :doc:`install/all_in_one`.
    2. Copy the content from the previous installation to `/opt/stackstorm/packs`
       and reload it with `st2ctl reload --register-all`.
    3. Adjust the content according to upgrade notes below. Test and ensure your automations work.
    4. Save the audit log files from ``/var/log/st2/*.audit.log`` for future reference.
       We do not migrate execution history to the new installation, but all the execution data is
       kept in these structured logs for audit purpose.

    .. warning:: Don't run All-in-one installer over |st2| existing st2 deployment.

Changes
~~~~~~~
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
* Mistral has implemented new YAQL function for referencing environment variables in the data
  context. The ``env()`` function replaces ``$.__env`` when referencing the environment variables.
  For example, ``$.__env.st2_execution_id`` becomes ``env().st2_execution_id``.
  **WARNING**: Referencing ``$.__env`` will lead to YAQL evaluation errors! Please update your workflows
  accordingly.
* Mistral has implemented new YAQL function for referencing task result. Given task1,
  the function call ``task(task1).result``, replaces ``$.task1`` when referencing result of task1.
  The old reference style will be fully deprecated in the next major release of Mistral, the
  OpenStack Mitaka release cycle.


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
