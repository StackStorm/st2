Adding Monitoring - Sensu
============================

`Sensu <http://www.sensuapp.org/>`_ is a popular monitoring tool. In this article, a sample sensu check will be setup and integrated with |st2|. Sensu check will emit an event as a webhook trigger to |st2|. A |st2| rule then matches the trigger based on some criteria and an action is
invoked.

Prerequisites
^^^^^^^^^^^^^

 - A box with sensu and st2 up and running. `st2express <https://github.com/StackStorm/st2express>`_ comes with |st2| and sensu installed. We are going to use that box as the example throughout this article.

 - If you are using your own box, please see :doc:`./../install/index` section for |st2| installation instructions. Sensu installation instructions are available `here <http://sensuapp.org/docs/latest/guide>`_.

Instructions
^^^^^^^^^^^^

1. Install `StackStorm sensu integration pack <https://github.com/StackStorm/st2contrib/tree/master/packs/sensu>`_. If you have already installed all the packs, skip this step.

::

    st2 run packs.install packs=sensu

2. A sample sensu rule is shown below.

.. sourcecode:: json

    {
       "name": "sensu.action-runners-rule",
       "description": "Sample rule that dogfoods st2.",

       "trigger": {
           "type": "sensu.event_handler",
           "parameters": {
           }
       },

       "criteria": {
           "trigger.check.name": {
               "pattern": "cron_check",
               "type": "equals"
           },
           "trigger.check.output": {
               "pattern": "CheckProcs CRITICAL*",
               "type": "matchregex"
           }
       },

       "action": {
           "ref": "core.local",
           "parameters": {
               "cmd": "echo \"{{trigger}}\" >> /tmp/sensu.webhook-sample.out"
           }
       },

       "enabled": true
    }

Copy the content of the sample rule to
``/opt/stackstorm/packs/sensu/rules/sensu_action_runners_rule.json``.

3. Now create the rule.

::

    st2 rule create /opt/stackstorm/packs/sensu/rules/sensu_action_runners_rule.json

4. Check if rule is listed.

::

    st2 rule list

You should see sensu.action-runners-rule listed.

::

    vagrant@st2express:~$ st2 rule list
    +--------------------------+--------------------------------+--------------------------------+
    | id                       | name                           | description                    |
    +--------------------------+--------------------------------+--------------------------------+
    | 54512b9b9c9938251e220033 | st2.webhook.github.pulls.merge | Sample rule dumping webhook    |
    |                          | .sample                        | payload to a file.             |
    | 54512b9b9c9938251e220035 | ec2.instance.down              | Email about down hosts that    |
    |                          |                                | are not marked as acknowledged |
    | 54512bb49c99382566f2ee5c | sensu.action-runners-rule      | Sample rule that dogfoods st2. |
    +--------------------------+--------------------------------+--------------------------------+

5. Create a sensu check json like below in the exact path specified.
(The sensu check monitors for exactly 10 |st2| action runners and alerts if the number of runners is less than 10.)

::

    cat /etc/sensu/conf.d/check_cron.json
    {
      "checks": {
        "cron_check": {
          "handlers": ["default", "st2"],
          "command": "/etc/sensu/plugins/check-procs.rb -p st2actionrunner -C 10 ",
          "interval": 60,
          "subscribers": [ "webservers" ]
        }
      }
    }

6. Create a sensu client config for the check above.

::

    cat /etc/sensu/conf.d/client.json
    {
      "client": {
        "name": "st2express",
        "address": "172.168.90.50",
        "subscriptions": [ "all", "webservers" ]
      }
    }

7. Create a sensu handler so we can integrate sensu with |st2|.

::

    cat /etc/sensu/conf.d/handler_st2.json
    {
        "handlers": {
            "st2": {
              "type": "pipe",
              "command": "/etc/sensu/handlers/st2_handler.py"
            },
            "default": {
              "type": "pipe",
              "command": "cat"
            }
        }
    }

8. Now copy the `st2_handler.py <https://github.com/StackStorm/st2contrib/blob/master/packs/sensu/etc/st2_handler.py>`_ from sensu pack to the sensu handlers dir.

::

    sudo cp /opt/stackstorm/packs/sensu/etc/st2_handler.py /etc/sensu/handlers/st2_handler.py
    sudo chmod +x /etc/sensu/handlers/st2_handler.py

9. The handler file now requires a configuration file (./config.yaml) to get st2 auth parameters.
Set the st2 credentials (username and password) in the config file. This is required for the
handler to work. The configuration file looks like below:

::

  ---
    st2_username: "testu"
    st2_password: ""
    st2_api_base_url: "http://localhost:9101/v1"
    st2_auth_base_url: "http://localhost:9100"

10. Now restart sensu server and client.

::

    sudo service sensu-server restart
    sudo service sensu-client restart

11. Create a sensu event by killing a runner process.

::

    ps auxww | grep st2actionrunner

Pick any pid. Kill it like so.

::

    sudo kill ${pid}

12. Wait for sensu event to be triggered. You can tail sensu-server logs like so:

::

    less /var/log/sensu/sensu-server.log

You'll see something like

::

    {"timestamp":"2014-10-29T17:21:11.941081+0000","level":"info","message":"handler output","handler":{"type":"pipe","command":"/etc/sensu/handlers/st2_handler.py","name":"st2"},"output":"Sent sensu event to |st2|. HTTP_CODE: 202\n"}

13. You can also check whether a trigger was registered by the handler with |st2|.

::

    st2 trigger list

You should see sensu.event_handler in the output.

14. You can see the list of sensu checks by invoking the |st2| check_list action.

::

    st2 run sensu.check_list

15. Now to verify whether an action has been invoked, cat the output file.

::

    cat /tmp/sensu.webhook-sample.out
    {u'action': u'create', u'check': {u'status': 2, u'executed': 1414603271, u'name': u'cron_check', u'handlers': [u'default', u'st2'], u'issued': 1414603271, u'interval': 60, u'command': u'/etc/sensu/plugins/check-procs.rb -p st2actionrunner -C 10 ', u'subscribers': [u'webservers'], u'duration': 0.046, u'output': u'CheckProcs CRITICAL: Found 9 matching processes; cmd /st2actionrunner/\n', u'history': [u'0', u'0', u'2', u'2', u'2', u'2', u'2', u'2', u'2', u'2', u'2', u'2', u'2', u'2', u'2']}, u'client': {u'timestamp': 1414603261, u'version': u'0.14.0', u'name': u'st2express', u'subscriptions': [u'all', u'webservers'], u'address': u'172.168.90.50'}, u'occurrences': 1, u'id': u'e056509c-9728-48cd-95cc-c41a4b62ae0e'}

16. Reset |st2| so you can bring back all the runners.

::

    sudo st2ctl restart

The instructions showed you how to invoke a very simple action when there is a sensu alert. In production environment, an action is a remediation action which would spin up an action runner. Look at :doc:`./../actions` section.
