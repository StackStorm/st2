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


Submitting debugging information to Plexxi
==========================================

Our wrapper script 'submit-debug-info.sh' will allow submit_debug_info.py to be customized for specific deployments (Plexxi's as an example :-) by loading a set of overrides from a YAML file. The following config options can now be specified:

* log_file_paths - an additional set of log files to gather
* conf_file_paths - an additional set of config files to gather
* s3_bucket - the S3 bucket to upload the archive to
* gpg - gpg key and fingerprint to use when encrypting the archive
* shell_commands - a list of shell commands to execute and capture the output from
* company_name - the company name to show in the interactive prompts and log messages

Sample Config file
------------------

---
log_file_paths:
    st2_log_files_path: /var/log/st2/*.log
    mistral_log_files_path: /var/log/mistral*.log
    rabbitmq_log_files_path: /var/log/rabbitmq/*
    message_files_path: /var/log/messages*
    salt_log_files_path: /var/log/*salt.log
    mongodb_log_files_path: /var/log/mongod/*
    nginx_log_files_path: /var/log/nginx/*
    yum_log_files_path: /var/log/yum.log
conf_file_paths:
    st2_config_file_path: /etc/st2/st2.conf
    mistral_config_file_path: /etc/mistral/mistral.conf
s3_bucket:
    url: https://plexxi-support.s3.amazonaws.com/
gpg:
    gpg_key_fingerprint: BDE989A1F308B18D29789C717064B11C82F62D6F
    gpg_key: |
          -----BEGIN PGP PUBLIC KEY BLOCK-----
          Version: GnuPG v1

          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
          =asEc
          -----END PGP PUBLIC KEY BLOCK----- 
shell_commands:
    cmd1: rpm -qa
company_name:
    name: Plexxi

To send debug information to Plexxi, simply invoke the command shown below:

.. sourcecode:: bash

    submit-debug-info.sh

    This will submit the following information to Plexxi: logs, configs, content, system_info, shell_commands
    Are you sure you want to proceed? [y/n] y
    2016-01-19 06:12:18,587  INFO - Collecting files...
    2016-01-19 06:12:19,602  INFO - Creating tarball...
    2016-01-19 06:12:19,708  INFO - Encrypting tarball...
    2016-01-19 06:12:43,949  INFO - Debug tarball successfully uploaded to Plexxi (name=st2-debug-output-70386ae8e4fe-2016-01-19-06:12:18.tar.gz.asc)
    2016-01-19 06:12:43,949  INFO - When communicating with support, please let them know the tarball name - st2-debug-output-70386ae8e4fe-2016-01-19-06:12:18.tar.gz.asc


We can pass through any command line arguments provided to st2-submit-debug-info

Sample examples:
---------------

* To run it an non-interactive mode using '--yes' option.

.. sourcecode:: bash

    submit-debug-info.sh --yes

    2016-01-19 06:25:09,024  INFO - Collecting files...
    2016-01-19 06:25:09,617  INFO - Creating tarball...
    2016-01-19 06:25:09,725  INFO - Encrypting tarball...
    2016-01-19 06:25:13,727  INFO - Debug tarball successfully uploaded to Plexxi (name=st2-debug-output-70386ae8e4fe-2016-01-19-06:25:09.tar.gz.asc)
    2016-01-19 06:25:13,727  INFO - When communicating with support, please let them know the tarball name - st2-debug-output-70386ae8e4fe-2016-01-19-06:25:09.tar.gz.asc

* To send a specific information to Plexxi or exclude a particular information using ``--exclude-<content>`` flag.

.. sourcecode:: bash

    submit-debug-info.sh --exclude-shell-commands

    This will submit the following information to Plexxi: logs, configs, content, system_info
    Are you sure you want to proceed? [y/n] y
    2016-01-19 06:28:25,533  INFO - Collecting files...
    2016-01-19 06:28:25,895  INFO - Creating tarball...
    2016-01-19 06:28:26,002  INFO - Encrypting tarball...
    2016-01-19 06:28:29,559  INFO - Debug tarball successfully uploaded to Plexxi (name=st2-debug-output-70386ae8e4fe-2016-01-19-06:28:25.tar.gz.asc)
    2016-01-19 06:28:29,559  INFO - When communicating with support, please let them know the tarball name - st2-debug-output-70386ae8e4fe-2016-01-19-06:28:25.tar.gz.asc
   
* To review the debugging information with encrypted and uploaded to Plexxi

.. sourcecode:: bash

    submit-debug-info.sh --review

    2016-01-19 06:19:04,911  INFO - Collecting files...
    2016-01-19 06:19:05,531  INFO - Creating tarball...
    2016-01-19 06:19:05,637  INFO - Debug tarball successfully generated and can be reviewed at: /tmp/st2-debug-output-70386ae8e4fe-2016-01-19-06:19:04.tar.gz 
