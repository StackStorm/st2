Webhooks
========

Webhooks allow you to integrate external systems with |st2| using HTTP
webhooks. Unlike sensors which use "pull" approach, webhooks use "push"
approach. This means they work by you pushing triggers directly to the |st2|
API using HTTP POST request.

What is a difference between sensors and webhooks?
--------------------------------------------------

Sensors integrate with external systems and services using poll approach
(sensors periodically reach out to an external system to retrieve data you are
interested in) and webhooks use push approach (your systems push data to the
|st2| API when an event you are interested in occurs).

Sensors are a preferred way of integration since they offer a more granular and
tighter integration.

On the other hand, webhooks come handy when you have an existing script or
software which you can easily modify to send a webhook to the |st2| API when an
event you are interested in occurs.

Another example where webhooks come handy is when you want to consume events
from a 3rd party services which already offer webhooks integration - an example
of such service includes Github.

Authentication
--------------

All the requests to the /webhooks endpoints needs to be authenticated in the
same way as other API requests. This means the request needs to contain a valid
authentication token. This token can either be provided in ``X-Auth-Token``
(usually used with your scripts where you can control request headers) or via
``?x-auth-token`` query parameter (usually used with 3rd party services such as
Github where you can only specify a URL).

Using a generic st2 webhook
---------------------------

By default, a generic webhook with a name ``st2`` is already registered. This
webhook allows you to push arbitrary triggers to the API.

Body of this request needs to be JSON and contain the following attributes:

* ``trigger`` - Name of the trigger (e.g. ``mypack.mytrigger``)
* ``payload`` - Object with a trigger payload.

Here is an example which shows how to send data to the generic webhook using
cURL and how to match on this data inside the rule criteria.

.. sourcecode:: bash

    curl -X POST http://127.0.0.1:9101/v1/webhooks/st2 -H "X-Auth-Token: matoken" -H "Content-Type: application/json" --data '{"trigger": "mypack.mytrigger", "payload": {"attribute1": "value1"}}'

Rule:

.. sourcecode:: yaml

    ...
    trigger:
            type: "mypack.mytrigger"

    criteria:
        trigger.attribute1
            type: "equals"
            pattern: "value1"

    action:
        ref: "mypack.myaction"
        parameters:
    ...

Keep in mind that the ``trigger.type`` attribute inside the rule definition
needs to be the same as the trigger name defined in the webhook payload body.

Registering a custom webhook
----------------------------

|st2| also supports registering custom webhooks. You can do that by specifying
``core.st2.webhook`` trigger inside a rule definition.

Here is an excerpt from a rule which registers a new webhook named ``sample``.

.. sourcecode:: yaml

    ...
    trigger:
            type: "core.st2.webhook"
            parameters:
                url: "sample"
    ...

Once this rule is created, you can use this webhook by POST-ing data to
``/v1/webhooks/sample``. The request body needs to be JSON and can contain
arbitrary data which you can match against in the rule criteria.

POST-ing data to a custom webhook will cause a trigger with the following
attributes to be dispatched:

* ``trigger`` - Trigger name.
* ``trigger.headers`` - Dictionary containing the request headers.
* ``trigger.body`` - Dictionary containing the request body.

Here is an example which shows how to send data to a custom webhook using
cURL and how to match on this data inside the rule criteria.

.. sourcecode:: bash

    curl -X POST http://127.0.0.1:9101/v1/webhooks/sample -H "X-Auth-Token: matoken" -H "Content-Type: application/json" --data '{"key1": "value1"}'

Rule:

.. sourcecode:: yaml

    ...
    trigger:
            type: "core.st2.webhook"
            parameters:
                url: "sample"

    criteria:
        trigger.body.key1:
            type: "equals"
            pattern: "value1"

    action:
        ref: "mypack.myaction"
        parameters:
    ...

Listing registered webhooks
---------------------------

To list all the registered webhooks you can use the CLI as shown below:

::

    st2 webhook list
