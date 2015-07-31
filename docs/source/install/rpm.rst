RedHat / Fedora
================

|st2| RPMs have been tested and precompiled for Fedora 20.

Deployment Script Installation
------------------------------


You can download and install the |st2| components, core content, and the accompanying control script by using our one step installer script.  You can download that script from our downloads site with the following command.

::

    curl -q -k -O https://downloads.stackstorm.net/releases/st2/scripts/st2_deploy.sh
    sudo chmod +x st2_deploy.sh

You can then run the script to download and install the |st2| packages
by simply passing in the version number. If no version number is given, it will default to the latest stable version.

::

    sudo ./st2_deploy.sh

This will download the latest stable build of |st2|.

---------------

Manual Installation
-------------------
Prerequisites
^^^^^^^^^^^^^

Yum
'''

-  mongodb
-  mongodb-server
-  python-pip
-  python-virtualenv
-  python-tox
-  gcc-c++
-  git-all

Pip
'''

The easiest way to install these is to use the requirements.txt file from the |st2| downloads server.  This is kept up to date for the version specified in the path.

::

    https://downloads.stackstorm.net/releases/st2/<VERSION>/requirements.txt

RabbitMQ
''''''''

In order to get the latest version of RabbitMQ, you will want to follow the directions on their site to do the installation.

::

    http://www.rabbitmq.com/install-rpm.html

Once you have RabbitMQ installed, you will need to run the following commands to enable certain plugins.

::

    rabbitmq-plugins enable rabbitmq_management
    service rabbitmq-server restart

You will also want to download the rabbitmqadmin script to make troubleshooting and management easier.

::

    curl -sS -o /usr/bin/rabbitmqadmin http://localhost:15672/cli/rabbitmqadmin
    chmod 755 /usr/bin/rabbitmqadmin


Installation
^^^^^^^^^^^^

You will need to download the following packages:

 - st2reactor
 - st2common
 - st2client
 - st2auth
 - st2api
 - st2actions
 - st2debug

The format of the RPM packages is like this: <component>-<version>-<build>.noarch.rpm

You can download the packages from this URL:
::

    https://downloads.stackstorm.net/releases/st2/0.12.1/rpms/current/

--------------

Configuration
^^^^^^^^^^^^^

SSH
'''

In order to run commands on remote you will need to setup a ssh keypair
and place the private key in a location accessible by the user that the
processes are running as.

See  :doc:`/install/config` for more information on setting up SSH access for a user.

Validating
^^^^^^^^^^^^^^^^^^^^^

.. include:: on_complete.rst
