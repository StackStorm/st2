RedHat / Fedora
================

|st2| RPMs have been tested and precompiled for Fedora 20.

---------------

.. warning::

   WOWZERS! A **deprecation** notice! Please note that this documentation and associated RPM packages are currently undergoing review and maintenance. Our core packages for CentOS and RedHat Enterprise (RHEL) are undergoing a complete overhaul to incorporate `**rpmvenv** <https://github.com/kevinconway/rpmvenv>` into our base packages. As such, please consider these instructions **DEPRECATED** for the time being. Hold tight, these packages and documentation are coming very soon.

   If you are feeling adventerous and want to attempt an installation using this method, we have left this documentation here for you to better understand the internals of the system as it currently exists

   In the meantime, please feel free to take a look at many of our installation methods, including our `All-in-one Installer </install/all_in_one.rst>`.


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
