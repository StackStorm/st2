Ubuntu / Debian
=================

|st2| debian packages have been tested and precompiled for Ubuntu 14.04.

--------------

.. TODO:: @jfryman rewprd the WORK-IN-PROGRESS/coming soon disclamer.

.. warning:: We are reworking Ubuntu/Debian packages and documentation. This page gives all the references to help a motivated reader figure out the installation. Proper documentation coming soon.

StackStorm APT Repositories
^^^^^^^^^^^^^^^^^^^^^^^^^^^
This repository contains latest stable version of StackStorm components
and dependencies:

::

  deb http://downloads.stackstorm.net/deb/ trusty_stable main


This repository contains latest in development version of StackStorm components
and dependencies:

::

  deb http://downloads.stackstorm.net/deb/ trusty_unstable main


Pre-requisites
^^^^^^^^^^^^^^

APT dependencies
''''''''''''''''

::

    aptlist='rabbitmq-server make python-virtualenv python-dev realpath python-pip mongodb mongodb-server gcc git mysql-server'
    apt-get install -y ${aptlist}

Pip dependencies
''''''''''''''''

Use :github_st2:`requirements.txt </requirements.txt>` file from the release brunch of st2 source.

::

    curl -q -k -O https://raw.githubusercontent.com/StackStorm/st2/<VERSION>/requirements.txt
    pip2.7 install -r requirements.txt

RabbitMQ
''''''''

Get the latest version of RabbitMQ, following the `RabbitMQ instllation instruction <http://www.rabbitmq.com/install-debian.html>`__. Once RabbitMQ is installed, run the following commands to enable management plugins.

::

    rabbitmq-plugins enable rabbitmq_management
    service rabbitmq-server restart

You will also want to download the rabbitmqadmin script to make troubleshooting and management easier.

::

    curl -sS -o /usr/bin/rabbitmqadmin http://localhost:15672/cli/rabbitmqadmin
    chmod 755 /usr/bin/rabbitmqadmin


Manual Installation
^^^^^^^^^^^^^^^^^^^

Complete instructions coming soon, along with updated packages. Meantime, read and follow the :github_st2:`st2_deploy.sh </tools/st2_deploy.sh>` script.


Configuration
^^^^^^^^^^^^^

See  :doc:`/config/config` for more information on setting up SSH access for a user.

