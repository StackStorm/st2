## Running from Sources

### Environment Prerequisites

Requirements:

- git
- Python, pip, virtualenv, tox
- MongoDB - http://docs.mongodb.org/manual/installation - with oplog enabled
- nodejs and npm - http://nodejs.org/

To setup the development environment from a vanilla Fedora image:

    yum install python-pip python-virtualenv python-tox gcc-c++ git-all screen icu libicu libicu-devel
    yum install mongodb mongodb-server
    # setup oplog for mongodb:
    echo "replSet = rs0" >> /etc/mongodb.conf
    echo "oplogSize = 100" >> /etc/mongodb.conf
    systemctl enable mongod
    systemctl restart mongod
    # give it few moments to spin up then initiate replication set
    sleep 10
    mongo --eval "rs.initiate()"
    yum install npm
    npm install -g bower
    npm install -g gulp

To setup the development environment via Vagrant:

    git clone https://github.com/StorminStanley/devenv.git
    cd devenv
    ./configure.sh dev
    vagrant up
    vagrant ssh

Refer to the [README](https://github.com/StorminStanley/devenv/README.md) under https://github.com/StorminStanley/devenv for additional details.


### Project Prerequisites

Once the environment is setup, clone the git repo, and make the project. This will create the python virtual environment under stanley, download and install required dependencies, and run tests.

    git clone https://github.com/StorminStanley/stanley.git
    cd stanley
    make all

### Running Stanley From Source

Create the directory /opt/stackstorm and change ownership to the user that will run the Stanley services.

    sudo mkdir -p /opt/stackstorm
    sudo chown -R OWNER:GROUP /opt/stackstorm   # Change ownership to appropriate user

Specify a user for running local and remote SSH actions: in conf/stanley.conf:

    [ssh_runner]
    user = stanley
    ssh_key_file = /home/vagrant/.ssh/stanley_rsa
    remote_dir = /tmp

In case you don't have a user for this purpose (as in case of devenv), there is number of steps you need to perform to create one and setup it to work with fabric_runner:

1. Create new user

        sudo adduser stanley


1. Create an `.ssh` folder inside stanley's home folder

        sudo mkdir -p /home/stanley/.ssh
        
1. Generate keypair for the user running Stanley services

        ssh-keygen -f ~/.ssh/stanley_rsa

1. Add service user public key to stanley's authorized_keys

        sudo sh -c 'cat ~/.ssh/stanley_rsa.pub >> /home/stanley/.ssh/authorized_keys'

1. Fix permissions

        sudo chown -R stanley:stanley /home/stanley/.ssh/

To run Stanley from source, it's assumed that python virtual environment is activated and in use.

    source virtualenv/bin/activate  # Activates the python virtual environment
    tools/lauchdev.sh start         # Launches all st2 services in screen sessions
    tools/lauchdev.sh stop          # Stops all st2 screen sessions and services

If the services are started successfully, you will see the following output.

	Starting all st2 servers...
	Changing working directory to /home/dzimine/share/stanley...
	Starting screen session st2-actionrunner...
	Starting screen session st2-api...
	Starting screen session st2-reactor...
	
	There are screens on:
		28158.st2-reactor	(09/25/2014 12:36:43 AM)	(Detached)
		28154.st2-api	(09/25/2014 12:36:43 AM)	(Detached)
		28143.st2-actionrunner	(09/25/2014 12:36:43 AM)	(Detached)
	3 Sockets in /var/run/screen/S-stanley.
	
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
	
Stanley can now be operated using the REST API, st2 CLI, and the st2client python client library. Hubot/Chat integration is also provided.


### Setup st2 CLI
If installed from source, the CLI client needs to be installed into the virtualenv:

    cd stanley/st2client
    python setup.py install

### Next
