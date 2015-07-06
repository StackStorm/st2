Run From Sources
=================

Environment Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~

Requirements:

-  git
-  python, pip, virtualenv, tox
-  MongoDB (http://docs.mongodb.org/manual/installation)
-  RabbitMQ (http://www.rabbitmq.com/download.html)
-  screen

Ubuntu
------

::

    apt-get install python-pip python-virtualenv python-dev gcc git make realpath screen
    apt-get install mongodb mongodb-server
    apt-get install rabbitmq-server

Fedora
------

::

    yum install python-pip python-virtualenv python-tox gcc-c++ git-all screen icu libicu libicu-devel

    yum install mongodb mongodb-server
    systemctl enable mongod
    systemctl restart mongod

    yum install rabbitmq-server
    systemctl enable rabbitmq-server
    systemctl restart rabbitmq-server

Optional Requirements
~~~~~~~~~~~~~~~~~~~~~

Mistral
-------
Mistral workflow engine also has its own requirements to the environment. For more information,
please refer to :github_mistral:`Mistral README <README.rst>`.

Project Requirements
~~~~~~~~~~~~~~~~~~~~

Once the environment is setup, clone the git repo, and make the project.
This will create the python virtual environment under |st2|, download
and install required dependencies, and run tests.

::

    git clone https://github.com/StackStorm/st2.git
    cd st2
    make requirements

Configure System User
~~~~~~~~~~~~~~~~~~~~~
Specify a user for running local and remote SSH actions. See :ref:`config-configure-ssh`. In st2/conf/st2.dev.conf, change ``ssh_key_file`` to point to the user's key file. ::

    [system_user]
    user = stanley
    ssh_key_file = /home/[current user]/.ssh/stanley_rsa

Running
~~~~~~~
Run the following to start |st2|. The script will start |st2| components in screen sessions. ::

    ./tools/launchdev.sh start

Additional commands: ::

    source virtualenv/bin/activate  # Activates the python virtual environment
    tools/launchdev.sh startclean    # Reset and launches all |st2| services in screen sessions
    tools/launchdev.sh start         # Launches all |st2| services in screen sessions
    tools/launchdev.sh stop          # Stops all |st2| screen sessions and services

If the services are started successfully, you will see the following
output. ::

    Starting all st2 servers...
    Changing working directory to /home/vagrant/st2/./tools/.....
    Using st2 config file: /home/vagrant/st2/./tools/../conf/st2.dev.conf
    Using content packs base dir: /opt/stackstorm/packs
    No Sockets found in /var/run/screen/S-vagrant.

    Starting screen session st2-api...
    Starting screen session st2-actionrunner...
        starting runner  1 ...
    No screen session found.
    Starting screen session st2-sensorcontainer
    Starting screen session st2-rulesengine...
    Starting screen session st2-resultstracker...
    Starting screen session st2-notifier...

    Registering sensors, actions, rules and aliases...
    ...

|st2| can now be operated using the REST API, |st2| CLI, and the
st2client python client library.

.. _setup-st2-cli:

Install |st2| CLI
~~~~~~~~~~~~~~~~~
The |st2| CLI client needs to be installed. It's not necessary to install this into the virtualenv. However, the client may need to be installed with sudo if not in the virtualenv. ::

    cd ./st2client
    python setup.py develop

Verify Installation
~~~~~~~~~~~~~~~~~~~
To make sure all the components are installed correctly... ::

    st2 --version
    st2 --help
    st2 action list
    st2 run core.local uname

Additional Makefile targets
~~~~~~~~~~~~~~~~~~~~~~~~~~~

 - ``make all`` creates virtualenv, installs dependencies, and runs tests
 - ``make tests`` runs all the tests
 - ``make lint`` runs lint tasks (flake8, pylint)
 - ``make docs`` compiles this documentation
 - ``make clean`` clears .pyc's and docs
 - ``make distclean`` runs `make clean` target and also drops virtualenv
 - ``make requirements`` installs python requirements
 - ``make virtualenv`` creates an empty virtual environment

Manual Testing
~~~~~~~~~~~~~~

In case you only need to test specific module, it might be reasonable to call `nosetests` directly.
Make sure your virtualenv is active then run:

::

    nosetests -v {project_name}/tests

or if you only want to run a test for specific file or even class or method, run:

::

    nosetests -v {project_name}/tests/{path_to_test_file}/{test_file}.py:{Classname}.{method_name}

.. rubric:: What's Next?

* **Get going with** :doc:`/start`.

.. include:: /engage.rst
