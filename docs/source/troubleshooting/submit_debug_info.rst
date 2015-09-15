.. _submit_debug_info_to_st2:

Submitting debugging information to StackStorm
==============================================

First step when trying to help you debug an issue or a problem you are having
is for us to try to reproduce the problem. To be able to do that, our setup
needs to resemble yours as closely as possible.

To save time and make yours and our life easier, the default distribution of
StackStorm includes a utility which allows you to easily and in a secure manner
send us the information we need to help you debug or troubleshoot an issue.

By default, this script sends us the following information:

* All the StackStorm services log files from ``/var/log/st2``
* Mistral service log file from ``/var/log/mistral.log``
* StackStorm and Mistral config file (``/etc/st2/st2.conf``,
  ``/etc/mistral/mistral.conf``). Prior to sending the config files we strip
  sensitive information such as database and queue access information.
* StackStorm content (integration packs) minus the pack configs.

All this information is bundled up in a tarball and encrypted using our
public key via public-key cryptography. Once submitted, this information
is only accessible to the StackStorm employees and it's used solely for
debugging purposes.

To send debug information to StackStorm, simply invoke the command shown
below:

.. sourcecode:: bash

    st2-submit-debug-info

    This will submit the following information to StackStorm: logs, configs, content, system_info
    Are you sure you want to proceed? [y/n] y
    2015-02-10 16:43:54,733  INFO - Collecting files...
    2015-02-10 16:43:55,714  INFO - Creating tarball...
    2015-02-10 16:43:55,892  INFO - Encrypting tarball...
    2015-02-10 16:44:02,591  INFO - Debug tarball successfully uploaded to StackStorm

By default, tool run in an interactive mode. If you want to run it an
non-interactive mode and assume "yes" as the answer to all the questions you
can use the ``--yes`` flag.

For example:

.. sourcecode:: bash

    st2-submit-debug-info --yes

    2015-02-10 16:45:36,074  INFO - Collecting files...
    2015-02-10 16:45:36,988  INFO - Creating tarball...
    2015-02-10 16:45:37,193  INFO - Encrypting tarball...
    2015-02-10 16:45:43,926  INFO - Debug tarball successfully uploaded to StackStorm

If you want to only send a specific information to StackStorm or exclude a
particular information you can use the ``--exclude-<content>`` flag.

For example, if you want to only send us log files, you would run the command
like this:

.. sourcecode:: bash

    st2-submit-debug-info --exclude-configs --exclude-content --exclude-system-info

Reviewing the debug information
-------------------------------

If you want to review and / or manipulate information (e.g. remove log lines
which you might find sensitive) which is sent to StackStorm, you can do that
using ``--review`` flag.

When this flag is used, the archive with debug information won't be encrypted
and uploaded to StackStorm.

.. sourcecode:: bash

    st2-submit-debug-info --review

    2015-02-10 17:43:49,016  INFO - Collecting files...
    2015-02-10 17:43:49,770  INFO - Creating tarball...
    2015-02-10 17:43:49,912  INFO - Debug tarball successfully generated and can be reviewed at: /tmp/st2-debug-output-vagrant-ubuntu-trusty-64-2015-02-10-17:43:49.tar.gz
