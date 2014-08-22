Install
======

### RPMs

Stanley RPMs have been tested and precompiled for Fedora 20.  In order to download them from the StackStorm release server you need to contact us to obtain login credentials.  

#### Deployment Script Installation

Once you have your credentials you can download our deployment script and use it to install all the prerequisites and the Stanley packages.  After downloading and running this script, you can jump straight to the Configuration section.

Download the following script, and edit the USER and PASS variables to match the credentials you received from StackStorm.

    curl -q -k -O https://<USERNAME>:<PASSWORD>@ops.stackstorm.net/releases/stanley/scripts/deploy_stan.sh

You can then run the script to download and install the Stanley packages by simply passing in the version number:

    sudo ./deploy_stan.sh 0.1.0

This will download the latest build of Stanley version 0.1.0.

---

#### Prerequisites
##### Yum

- mongodb
- mongodb-server
- python-pip
- python-virtualenv
- python-tox 
- gcc-c++ 
- git-all


##### Pip

The following packages are required by Stanley to run but will be installed by the deploy_stan.sh script if it is used.

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

#### Manual Installation

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

---

#### Configuration

##### MongoDB

Stanley requires replication to be enabled in MongoDB.  Add these lines to your mongo.conf file:

    echo "replSet = rs0" >> /etc/mongodb.conf
    echo "oplogSize = 100" >> /etc/mongodb.conf
    echo -e '127.0.0.1'\\t`hostname` >> /etc/hosts


MongoDB will need to be started and enabled by default.

    sudo systemctl restart mongod.service
    sudo systemctl enable mongod.service

Initiate the replica set

    mongo --eval "rs.initiate()"


##### SSH

In order to run commands on remote you will need to setup a ssh keypair and place the private key in a location accessible by the user that the processes are running as.

By default, the username is Stanley, and the private key is located at /home/stanley/.ssh/stanley_rsa

These options can be changed in the Stanley configuration file:

    /etc/stanley/stanley.conf

#### Starting and Stopping

The command to start and or stop stanley is 'st2run'.

    sudo st2run start|stop|restart|status


