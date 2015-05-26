ST2 Self-Test Pack
==================

About
-----
This pack contains a set of end-to-end tests, that allow to verify st2, using st2 itself. Currently the set contains the following tests:

* **tests.test_packs_pack** verifies functionality provided by [Packs pack](http://docs.stackstorm.com/packs.html#getting-a-pack).
* **tests.test_quickstart** follows the set of commands described in [Explore StackStorm with CLI](http://docs.stackstorm.com/start.html#explore-st2-with-cli) and [Work with Actions](http://docs.stackstorm.com/start.html#work-with-actions) sections of [Quick Start](http://docs.stackstorm.com/start.html)
* **tests.test_quickstart_rules** tests rule creation, validation and deletion, as described in [Define a Rule](http://docs.stackstorm.com/start.html#define-a-rule) section of [Quick Start](http://docs.stackstorm.com/start.html)
* **tests.test_quickstart_key** verifies key create/get example, used in [Datastore](http://docs.stackstorm.com/start.html#datastore) section of [Quick Start](http://docs.stackstorm.com/start.html)

All tests utilize [ActionChain](http://docs.stackstorm.com/actionchain.html).

Usage
-----
When |st2| is installed using all-in-one installation with [st2_deploy.sh](http://docs.stackstorm.com/install/index.html), the test pack can be used as part of the [self-check script](http://docs.stackstorm.com/troubleshooting.html#running-self-verification). Alternatively, each of the tests can be executed as follows:

1. Switch to `root` user and save an authentication token into `ST2_AUTH_TOKEN` variable:

.. code-block:: bash

     sudo su
     export ST2_AUTH_TOKEN=`st2 auth testu -p testp -t`

2. Check if ``tests`` pack is installed; if it's not installed, install it using usual pack installation routine. For example:

.. code-block:: bash

     sudo cp -r /usr/share/stackstorm/tests /opt/stackstorm/packs/
     st2ctl reload --register-all

3. Run actions using ``st2 run test_name token=${ST2_AUTH_TOKEN}``:

.. code-block:: bash

     st2 run tests.test_packs_pack token=${ST2_AUTH_TOKEN}
     st2 run tests.test_quickstart token=${ST2_AUTH_TOKEN}
     st2 run tests.test_quickstart_rules token=${ST2_AUTH_TOKEN}
     st2 run tests.test_quickstart_key token=${ST2_AUTH_TOKEN}
