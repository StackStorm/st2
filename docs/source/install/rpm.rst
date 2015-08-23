RedHat / Fedora
================

|st2| RPMs have been tested and precompiled for Fedora 20.

---------------


.. TODO:: @jfryman rewprd the WORK-IN-PROGRESS/coming soon disclamer.

.. warning:: We are reworking RedHat/Fedora packages and documentation. This page gives all the references to help a motivated reader figure out the installation. Proper documentation coming soon.

StackStorm YUM Repositories
^^^^^^^^^^^^^^^^^^^^^^^^^^^


This repository contains StackStorm dependencies:

::

  [st2-f20-deps]
  Name=StackStorm Dependencies Fedora repository
  baseurl=http://downloads.stackstorm.net/rpm/fedora/20/deps/
  enabled=1
  gpgcheck=0

This repository contains latest stable version of StackStorm components:

::

  [st2-f20-components]
  Name=StackStorm Dependencies Fedora repository
  baseurl=http://downloads.stackstorm.net/rpm/fedora/20/stable/
  enabled=1
  gpgcheck=0


This repository contains latest in development version of StackStorm components.

::

  [st2-f20-components]
  Name=StackStorm Dependencies Fedora repository
  baseurl=http://downloads.stackstorm.net/rpm/fedora/20/unstable/
  enabled=1
  gpgcheck=0


Prerequisites
^^^^^^^^^^^^^

Yum dependencies
''''''''''''''''

-  mongodb
-  mongodb-server
-  python-pip
-  python-virtualenv
-  python-tox
-  gcc-c++
-  git-all

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
