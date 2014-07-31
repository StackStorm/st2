St2 Stanley
======

## Installing from packages
See [Install.md](Install.md)

## Running from sources
Install prerequisites. See Prerequisites in [main README.md](../Readme.md)

From stanley root, run make. This creates virtualenv, installs all dependencies adn runs the tests. 

	make all


Activatge virtual environment, start and stop st2 services:

	source virtualenv/bin/activate # Activates virtual environment 
	tools/lauchdev.sh start  # Launches all st2 services 
	tools/lauchdev.sh stop  # Stops all st2 services
		
Note: If you are running from sources, anything below assumes an activated python virtualenv. 

Now you can operate the system via CLI, via REST API, and via s2client Python library. 

## Activate and use CLI
If installed from sources, you need to setup the CLI client into the virtualenv:
	
	cd st2client
	setup.py
	st2 --help

Some examples of using CLI: 

	st2 action list
	st2 run {action} {parameters}
	st2 trigger list
	st2 rule list

**TODO:**  add sample command to run action 


## Adding a Rule
Create a rule JSON definition. See an example at [Stanley/contrib/examples/rules/sample-rule.json](../contrib/examples/rules/sample-rule.json) for the rule structure. Look at [../contrib/sandbox/packages/](../contrib/sandbox/packages/) for more sample rules. 
	
**TODO:** fix  rules in contrib/sandbox/packages to confirm to new rule schema. 

**TODO:** draw a sample with here with commenst on required and optional fields. 

Deploy the rule:

	st2 rule create path/to/rule.json


#### TEMP: Configure Timer and Webhook
Rule is supposed to create and configure triggers on a fly. So that when you use trigger=timer, or trigger=webhook you give it parameters 

	./rule.json:
	{ "name": "myrule",
    "trigger": {
        "name": "timer"
        "parameters": {
        	// timer configuration
        }
    },
    ...

This is currently broken. 
This will be fixed before we show it outside friends & family. For now, do the following: 

#### To configure timer:
1. Edit `{stanley}/st2reactor/st2reactor/contrib/sensors/st2_timer_sensor.yaml`, create a new named timer triggers. 
2. Reboot Stanley `tools/launch.sh stop & tools/launch.sh start`. 
1. Use these named timer triggers in your rule,

		./rule.json:
		{ "name": "myrule",
	    "trigger": {
    	    "name": "timer.30s"
	    ...    

####To configure Web hook:
1. Go to `{stanley}/st2reactor/st2reactor/contrib/sensors/st2_generic_webhook_sensor.yaml`, add a string there. This string will serve both as a name of the webhook trigger, and a subpath to the url. For example, call it "webhookname".
2. Reboot Stanley `tools/launch.sh stop & tools/launch.sh start`. 
1. The webhook is now listening on http://{host}:6001/webhooks/generic/mywebhookname
1. Register the webhook trigger, named "mywebhookname". 
Create a json file 
		
		./mywebhooktrigger.json
	 	{
    		"name": "mywebhookname",
    		"description": 'call it yourname.webhooktrigger',
    		"payload_info": ["trigger-param-1", "trigger-param-2"]
		}

	Call CLI:
		
		st2 trigger create mywebhooktrigger.json
	**TODO:** add curl example. 
		
1. Use the trigger in a rule: 

	 		./rule.json:
			{ "name": "my rule",
	    	"trigger": {
    	    	"name": "mywebhookname"
	    	...    

Once again, this will all be taken care for you really soon. 

## Creating Custom Actions
See [actions.md](actions.md)

## Creating Custom Sensors
See [sensors.md](sensors.md)

