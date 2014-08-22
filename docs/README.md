St2 Stanley
======

## Installing from Packages
See [Install.md](install.md)

## Running from Sources

### Environment Prerequisites

Requirements:

- git
- Python, pip, virtualenv, tox
- MongoDB - http://docs.mongodb.org/manual/installation - with oplog enabled
- Web UI
    - nodejs and npm - http://nodejs.org/
    - [bower](http://bower.io/)
    - [gulp.js](http://gulpjs.com/)

To setup the development environment from a vanilla Fedora image:

    yum install python-pip python-virtualenv python-tox gcc-c++ git-all screen icu libicu libicu-devel
    yum install mongodb mongodb-server
    # setup oplog for mongodb:
    echo "replSet = rs0" >> /etc/mongodb.conf
    echo "oplogSize = 100" >> /etc/mongodb.conf
    systemctl enable mongod
    systemctl start mongod
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

### Running Stanley

Create the directory /opt/stackstorm and change ownership to the user that will run the Stanley services.

    sudo mkdir -p /opt/stackstorm
    sudo chown -R OWNER:GROUP /opt/stackstorm   # Change ownership to appropriate user

Specify a user for running local and remote SSH actions: in conf/stanley.conf:

    [fabric_runner]
    user = stanley
    ssh_key_file = /home/vagrant/.ssh/stanley_rsa
    remote_dir = /tmp

In case you don't have a user for this purpose (as in case of devenv), there is number of steps you need to perform to create one and setup it to work with fabric_runner:

1. Create new user

        sudo adduser stanley

2. Generate keypair for the user running Stanley services

        ssh-keygen -f ~/.ssh/stanley_rsa

3. Create an `.ssh` folder inside stanley's home folder

        sudo mkdir -p /home/stanley/.ssh

4. Add service user public key to stanley's authorized_keys

        sudo sh -c 'cat ~/.ssh/stanley_rsa.pub >> /home/stanley/.ssh/authorized_keys'

5. Fix permissions

        sudo chown -R stanley:stanley /home/stanley/.ssh/

To run Stanley from source, it's assumed that python virtual environment is activated and in use.

    source virtualenv/bin/activate  # Activates the python virtual environment
    tools/lauchdev.sh start         # Launches all st2 services in screen sessions
    tools/lauchdev.sh stop          # Stops all st2 screen sessions and services

If the services are started successfully, you will see the following output.

    Starting all st2 servers...
    Changing working directory to /home/vagrant/stanley...
    Starting screen session st2-datastore...
    Starting screen session st2-actionrunner...
    Starting screen session st2-action...
    Starting screen session st2-reactor...
    Starting screen session st2-reactorcontroller...

    There are screens on:
        7814.st2-reactorcontroller  (Detached)
        7811.st2-reactor    (Detached)
        7808.st2-action (Detached)
        7805.st2-actionrunner   (Detached)
        7802.st2-datastore  (Detached)
    5 Sockets in /var/run/screen/S-vagrant.

Stanley can now be operated using the REST API, st2 CLI, and the st2client python client library. [Hubot/Chat integration](hubot.md) is also provided.

### Setup st2 CLI
If installed from source, the CLI client needs to be installed into the virtualenv:

    cd stanley/st2client
    python setup.py install

#### CLI Usage Examples
Please refer to the [Terminology](#Terminology) section below for definition of terms and commands.

    st2 -h
    st2 action list
    st2 trigger list
    st2 rule list
    st2 run local -- ls -l
    st2 run remote host='host.1, host.2' user='myuser' -- ls -l

For more details on using the CLI and python client, please visit the [client](client.md) section.

## Terminology

| Term    | Description |
|---------|-------------|
| Sensor  | An adapter to convert an external event to a form stanley understands. This is usually a piece of python code. |
| Trigger | An external event that is mapped to a stanley input. It is the stanley invocation point. |
| Rule    | A specification to invoke an "action" on a "trigger" selectively based on some criteria. |
| Action  | An activity that user can run manually or use up in a rule as a response to the external event. |

## Running Actions
Actions from action library can be invoked from st2 CLI, REST API, or used in the rules.

Lits the avaialbe actions by `st2 action list`. To introspect an action, do `st2 action <actionname> get`, or, `st2 run <actionname> --h ( --help)` This shows action parameters so that you know how to call them or refer them in the rules. To run the action from cli, do `st2 run <actionname> -- key=value positional arguments`. Some examples of using out-of-box actions:

	st2 run http url="http://localhost:9101/actions" method="GET"

	st2 run local -- uname -a

	# Assuming SSH access is configured for the hosts
	st2 run remote host='abc.example.com, cde.example.com' user='mysshuser' -- ls -l

Note: for 'local' and 'remote' actions, we use `--` to separate action parameters to ensure that options keys, like `-l` or `-a` are properly passed to the action. You can Use the the `cmd` parameter to pass crasily complex commands.

	st2 run remote host='myhost' cmd="for u in bob phill luke; do echo \"Logins by $u per day:\"; grep $u /var/log/secure | grep opened |awk '{print $1 \"-\" $2}' | uniq -c | sort; done"


## Defining Rules
A rule maps a trigger to an action: if THIS triggers, run THAT action. It takes trigger parameters, sets matching criteria, and maps trigger output parameters to action input parameters.

To see a list of available triggers: `st2 trigger list`. The most generic ones are timer triggers, webhook trigger `st2.webhook`, and `st2.generic.actiontrigger` that is fired on each action completion. For more interesting triggers, explore sensors under [contrib/sandbox/](../contrib/sandbox/).

Rule is defined as JSON. The following is a sample rule definition structure and a listing of the required and optional elements.

    {
            "name": "rule_name",                       # required
            "description": "Some test rule.",          # optional

            "trigger": {                               # required
                "name": "trigger_name"
            },

            "criteria": {                              # optional
                ...
            },

            "action": {                                # required
                "name": "action_name",
                "parameters": {                        # optional
                        ...
                }
            },

            "enabled": true                            # required
    }

The example at [Stanley/contrib/examples/rules/sample-rule-with-webhook.json](../contrib/examples/rules/sample-rule-with-webhook.json) takes a webhook and appends a payload to the file, but only if the name matches:

	{
	    "name": "st2.webhook-sample",
	    "description": "Sample rule dumping webhook payload to a file.",

	    "trigger": {
	        "type": "st2.webhook",
	        "parameters": {
	            "url": "sample"
	        }
	    },

	    "criteria": {
	        "trigger.name": {
	            "pattern": "Joe",
	            "type": "equals"
	         }
	    },

	    "action": {
	        "name": "local",
	        "parameters": {
	            "cmd": "echo \"{{trigger}}\" >> /tmp/st2.webhook-sample.out"
	        }
	    },

	    "enabled": true
	}

To refer trigger payload in the action, use {{trigger}}. If trigger payload is valid JSON, refer the parameters with {{trigger.path.to.parameter}} in trigger.

Here is how to deploy the rule:

	# NOTE: The convention is to keep active rules in /opt/stackstorm/rules.
	cp contrib/examples/rules/sample-rule-with-webhook.json /opt/stackstorm/rules/

	st2 rule create /opt/stackstorm/rules/sample-rule-with-webhook.json
	st2 rule list
	st2 rule get st2.webhook-sample

Once the rule is created, the webhook begins to listen on `http://{host}:6001/webhooks/generic/{url}`. Fire the post, check out the file and see that it appends the payload if the name=Joe.

	curl http://localhost:6001/webhooks/generic/sample -d '{"foo": "bar", "name": "Joe"}' -H 'Content-Type: application/json'
	tail /tmp/st2.webhook-sample.out

Criteria in the rule is expressed as:

	criteria: {
	     "trigger.payload_parameter_name": {
	     	"pattern" : "value",
	        "type": "matchregex"
	      }
	      ...
	}


Current criteria types are: `'matchregex', 'eq' (or 'equals'), 'lt' (or 'lessthan'), 'gt' (or 'greaterthan'), 'td_lt' (or 'timediff_lt'), 'td_gt' (or 'timediff_gt')`.

**DEV NOTE:** The criterias are defined in [Stanley/st2common/st2common/operators.py](../st2common/st2common/operators.py), if you miss some code it up and submit a patch :)

See more rule examples at [Stanley/contrib/examples/rules/](../contrib/examples/rules/). The directory [../contrib/sandbox/packages/](../contrib/sandbox/packages/) contains some more rules.


## Storing Reusable Parameters
The datastore service allow users to store common parameters and their values as key value pairs within Stanley for reuse in sensors, actions, and rules. It is handy to store some system or user variables (e.g. configurations), refer them in a rule by `{{system.my_parameter}}`, or use in custom sensors and actions. Please refer to the [datastore](datastore.md) section for usage.

## Defining Custom Actions
See [actions.md](actions.md) for more details on how to create custom actions.

## Defining Custom Triggers

To introduce a custom trigger, you need to write a sensor - a code that does the job of transferring the external event into Stanley trigger. See [sensors.md](sensors.md) for more details on how to write sensors.
