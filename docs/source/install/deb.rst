Ubuntu / Debian
=================

|st2| debian packages have been tested and precompiled for Ubuntu 14.04.

--------------

.. warning::

   WOWZERS! A **deprecation** notice! Please note that this documentation and associated DEB packages are undergoing review and maintenance. Our core packages for Debian and Ubuntu are undergoing a complete overhaul to incorporate `dh-virtualenv <http://dh-virtualenv.readthedocs.org>`_ into our base packages. As such, please consider these instructions **DEPRECATED** for the time being. Hold tight, these packages and docs are coming very soon.

   If you are feeling adventurous and want to attempt an installation using this method, we have left this documentation here for you to better understand the internals of the system as it currently exists

   In the meantime, please feel free to take a look at many of our installation methods, including our `All-in-one Installer </install/all_in_one.rst>`_.


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

Complete instructions coming soon, along with updated packages. Meantime, read and follow the :github_st2:`st2_deploy.sh </tools/st2_deploy.sh>` script or explore `Puppet modules <https://github.com/stackstorm/puppet-st2>`_.


Configuration
^^^^^^^^^^^^^

See  :doc:`/config/config` for more information on setting up SSH access for a user.

