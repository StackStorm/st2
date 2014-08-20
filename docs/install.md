Install
======

### RPMs

Stanley RPMs have been tested and precompiled for Fedora 20.  In order to download them from the StackStorm release server you need to contact us to obtain login credentials.  

#### Prerequisites
##### Yum

- mongodb
- mongodb-server
- python-pip
- python-virtualenv
- python-tox 
- gcc-c++ 
- git-all


    sudo yum install -y python-pip python-virtualenv python-tox gcc-c++ git-all mongodb mongodb-server

##### Pip

- pbr>=0.5.21,<1.0
- pymongo
- mongoengine
- oslo.config
- six
- eventlet>=0.13.0
- pecan
- WSME
- jinja2
- requests
- flask
- flask-jsonschema
- prettytable
- pyyaml
- apscheduler>=3.0.0rc1
- python-dateutil
- paramiko
- git+https://github.com/StackStorm/fabric.git@stanley-patched
- jsonschema>=2.3.0


    sudo pip install -U all ze packages

#### Installation

Once you have the credentials you can download the packages from:

https://ops.stackstorm.net/releases/stanley/<VERSION>/rpms/current/

The required packages are listed below:

    st2actioncontroller-<VERSION>-<BUILD>.noarch.rpm
    st2actionrunnercontroller-<VERSION>-<BUILD>.noarch.rpm
    st2common-<VERSION>-<BUILD>.noarch.rpm
    st2client-<VERSION>-<BUILD>.noarch.rpm
    st2datastore-<VERSION>-<BUILD>.noarch.rpm
    st2reactor-<VERSION>-<BUILD>.noarch.rpm
    st2reactorcontroller-<VERSION>-<BUILD>.noarch.rpm

Download the following script, and edit the USER and PASS variables to match the credentials you received from StackStorm.

    https://ops.stackstorm.net/releases/stanley/scripts/deploy_stan.sh

You can then run the script to download and install the Stanley packages by simply passing in the version number:

    ./deploy_stan.sh 0.2.0

This will download the latest build of Stanley version 0.2.0.

#### Configuration

In order to run commands on remote you will need to setup a ssh keypair and place the private key in a location accessible by the user that the processes are running as.

By default, the username is Stanley, and the private key is located at /home/stanley/.ssh/stanley_rsa

These options can be changed in the Stanley configuration file:

    /etc/stanley/stanley.conf

#### Starting and Stopping

The command to start and or stop stanley is 'st2run'.

    st2run start|stop|restart|status


