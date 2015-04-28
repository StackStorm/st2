Datastore
===============================

The goal of the datastore service is to allow users to store common
parameters and their values within |st2| for reuse in the definition
of sensors, actions, and rules. The datastore service store the data as
a key value pair and they can be get/set using the |st2| CLI or the |st2|
python client. From the sensor and action plugins, since they are
implemented in python, the key value pairs are accessed from the |st2|
python client. For rule definitions in YAML/JSON, the key value pairs are
referenced with a specific string substitution syntax and the references
are resolved on rule evaluation.

Storing and Retrieving Key Value Pairs from CLI
-----------------------------------------------

Set a value of a key value pair.

::

    st2 key set os_keystone_endpoint http://localhost:5000/v2.0
    st2 key set aws_cfn_endpoint https://cloudformation.us-west-1.amazonaws.com

Load a list of key value pairs from a JSON file. The following is the
JSON example using the same keys from the create examples above.

::

    [
        {
            "os_keystone_endpoint": "http://localhost:5000/v2.0",
            "aws_cfn_endpoint": "https://cloudformation.us-west-1.amazonaws.com"
        }
    ]

    st2 key load mydata.json

The load command also allows you to directly load the output of "key list -j"
command. This is useful if you want to migrate datastore items from a different
cluster or if you want to version control the datastore items and load the from
version controlled files.

::

    st2 key list -j > mydata.json
    st2 key load mydata.json

Get individual key value pair or list all.

::

    st2 key list
    st2 key get os_keystone_endpoint
    st2 key get os_keystone_endpoint -j

Update an existing key value pair.

::

    st2 key set os_keystone_endpoint http://localhost:5000/v3

Delete an existing key value pair.

::

    st2 key delete os_keystone_endpoint

Storing and Retrieving from Python Client
-----------------------------------------

Create new key value pairs. The |st2| API endpoint is set either via
the Client init (base\_url) or from environment variable
(ST2\_BASE\_URL). The default ports for the API servers are assumed.

::

    >>> from st2client.client import Client
    >>> from st2client.models import KeyValuePair
    >>> client = Client(base_url='http://localhost')
    >>> client.keys.update(models.KeyValuePair(name='os_keystone_endpoint', value='http://localhost:5000/v2.0'))

Get individual key value pair or list all.

::

    >>> keys = client.keys.get_all()
    >>> os_keystone_endpoint = client.keys.get_by_name(name='os_keystone_endpoint')
    >>> os_keystone_endpoint.value
    u'http://localhost:5000/v2.0'

Update an existing key value pair.

::

    >>> os_keystone_endpoint = client.keys.get_by_name(name='os_keystone_endpoint')
    >>> os_keystone_endpoint.value = 'http://localhost:5000/v3'
    >>> client.keys.update(os_keystone_endpoint)

Delete an existing key value pair.

::

    >>> os_keystone_endpoint = client.keys.get_by_name(name='os_keystone_endpoint')
    >>> client.keys.delete(os_keystone_endpoint)

Referencing Key Value Pair in Rule Definition
---------------------------------------------

Key value pairs are referenced via specific string substitution syntax
in rules. In general, variable for substitution is enclosed with double
brackets (i.e. **{{var1}}**). To refer to a key value pair, prefix the
variable name with "system" (i.e.
**{{system.os\_keystone\_endpoint}}**). An example rule is provided
below. Please refer to the documentation section for Rules on rule
related syntax.

::

    {
        "name": "daily_clean_up_rule",
        "trigger": {
            "name": "st2.timer.daily"
        },
        "enabled": true,
        "action": {
            "name": "daily_clean_up_action",
            "parameters": {
                "os_keystone_endpoint": "{{system.os_keystone_endpoint}}"
            }
        }
    }

