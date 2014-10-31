Run From Sources
=================

Environment Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~

Requirements:

-  git
-  python, pip, virtualenv, tox
-  MongoDB (http://docs.mongodb.org/manual/installation)
-  RabbitMQ (http://www.rabbitmq.com/download.html)
-  NodeJS and NPM (http://nodejs.org/)

To setup the development environment starting from a vanilla Fedora image:

::

    yum install python-pip python-virtualenv python-tox gcc-c++ git-all screen icu libicu libicu-devel

    yum install mongodb mongodb-server
    systemctl enable mongod
    systemctl restart mongod

    yum install rabbitmq-server
    systemctl enable rabbitmq-server
    systemctl restart rabbitmq-server

    yum install npm
    npm install -g bower gulp

Mistral workflow engine also has its own requirements to the environment. For more information, please refer to :doc:`/mistral`.

To setup the development environment via Vagrant:

::

    git clone https://github.com/StackStorm/devenv.git
    cd devenv
    ./configure.sh dev
    vagrant up
    vagrant ssh

Refer to the
`README <https://github.com/StackStorm/devenv/README.md>`__ under
https://github.com/StackStorm/devenv for additional details.

Project Prerequisites
~~~~~~~~~~~~~~~~~~~~~

Once the environment is setup, clone the git repo, and make the project.
This will create the python virtual environment under st2, download
and install required dependencies, and run tests.

::

    git clone https://github.com/StackStorm/st2.git
    cd st2
    make all

Configuration
~~~~~~~~~~~~~

Specify a user for running local and remote SSH actions: in
conf/st2.conf:

::

    [ssh_runner]
    user = stanley
    ssh_key_file = /home/[current user]/.ssh/stanley_rsa

In case you don't have a user for this purpose (as in case of devenv),
there is number of steps you need to perform to create one and setup it
to work with fabric\_runner:

1. Create new user

   ::

       sudo adduser stanley

2. Create an ``.ssh`` folder inside his home folder

   ::

       sudo mkdir -p /home/stanley/.ssh

3. Generate keypair for the user running st2 services

   ::

       ssh-keygen -f ~/.ssh/stanley_rsa

4. Add service user public key to user's authorized\_keys

   ::

       sudo sh -c 'cat ~/.ssh/stanley_rsa.pub >> /home/stanley/.ssh/authorized_keys'

5. Fix permissions

   ::

       sudo chown -R stanley:stanley /home/stanley/.ssh/

For more information on config parameters see :doc:`/install/config`.

Running st2 From Source
~~~~~~~~~~~~~~~~~~~~~~~

To run st2 from source, it's assumed that python virtual environment
is activated and in use.

::

    source virtualenv/bin/activate  # Activates the python virtual environment
    tools/lauchdev.sh start         # Launches all st2 services in screen sessions
    tools/lauchdev.sh stop          # Stops all st2 screen sessions and services

If the services are started successfully, you will see the following
output.

::

    Starting all st2 servers...
    Changing working directory to /home/stanley/st2...
    Starting screen session st2-actionrunner...
    Starting screen session st2-api...
    Starting screen session st2-reactor...

    There are screens on:
        28158.st2-reactor   (09/25/2014 12:36:43 AM)    (Detached)
        28154.st2-api   (09/25/2014 12:36:43 AM)    (Detached)
        28143.st2-actionrunner  (09/25/2014 12:36:43 AM)    (Detached)
    3 Sockets in /var/run/screen/S-st2.

    Registering actions and rules...
    2014-09-25 00:36:44,670 INFO [-] Database details - dbname:st2, host:0.0.0.0, port:27017
    2014-09-25 00:36:44,676 INFO [-] Start : register default RunnerTypes.
    2014-09-25 00:36:44,689 INFO [-] RunnerType name=run-local exists.
    2014-09-25 00:36:44,697 INFO [-] RunnerType name=run-remote exists.
    2014-09-25 00:36:44,708 INFO [-] RunnerType name=http-runner exists.
    2014-09-25 00:36:44,720 INFO [-] RunnerType name=workflow exists.
    2014-09-25 00:36:44,729 INFO [-] RunnerType name=action-chain exists.
    2014-09-25 00:36:44,732 INFO [-] End : register default RunnerTypes.
    ...
    ...

st2 can now be operated using the REST API, st2 CLI, and the
st2client python client library. Hubot/Chat integration is also
provided.

Setup st2 CLI
~~~~~~~~~~~~~

If installed from source, the CLI client needs to be installed into the
virtualenv:

::

    cd st2/st2client
    python setup.py install

Testing
~~~~~~~

To make sure all the components were installed correctly:

::

    st2 --help
    st2 action list
    st2 run core.local uname

.. rubric:: What's Next?

* **Get going with** :doc:`/start`.

.. include:: /engage.rst
