Ubuntu / Debian
=================

|st2| debian packages have been tested and precompiled for Ubuntu 14.04.

--------------

Prerequisites
^^^^^^^^^^^^^

APT
'''

::

    aptlist='rabbitmq-server make python-virtualenv python-dev realpath python-pip mongodb mongodb-server gcc git mysql-server'
    apt-get install -y ${aptlist}

Pip
'''

The easiest way to install these is to use the requirements.txt file from the |st2| downloads server.  This is kept up to date for the version specified in the path.

::

    curl -q -k -O https://downloads.stackstorm.net/releases/st2/0.9.2/requirements.txt
    pip install -r requirements.txt

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

--------------

Manual Installation
^^^^^^^^^^^^^^^^^^^

You will need to download the following packages:

 - st2reactor
 - st2common
 - st2client
 - st2auth
 - st2api
 - st2actions
 - st2debug

The format of the DEB packages is like this: <component>_<version>-<build>_amd64.deb

You can download the packages from this URL:
::

    https://downloads.stackstorm.net/releases/st2/0.9.2/debs/current/

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
