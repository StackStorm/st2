Policies
========

.. note::

    Policy is currently an experimental feature and may subject to bugs and design changes.

To list the types of policy that is available for configuration, run the command ``st2 policy-type list``.

Policy configuration files are expected to be located under the ``policies`` folder in related packs, similar to actions and rules. Policies can be loaded into |st2| via ``st2ctl reload --register-policies``. Once policies are loaded into |st2|, run the command ``st2 policy list`` to view the list of policies in effect.

Concurrency
-----------

The concurrency policy enforces the number of executions that can run simultaneously for a specified action. There are two forms of concurrency policy: ``action.concurrency`` and ``action.concurrency.attr``.

The ``action.concurrency`` policy basically limites the concurrenct executions for the action. The following is an example of a policy file with concurrency defined for ``demo.my_action``. Please note that the resource_ref and policy_type are the fully qualified name for the action and policy type respectively. The ``threshold`` parameter defines how many concurrency instances allowed. In this example, no more than 10 instances of ``demo.my_action`` can be run simultaneously. Any execution requests passed threshold will be postponed.

.. sourcecode:: YAML

    name: my_action.concurrency
    description: Limits the concurrent executions for my action.
    enabled: true
    resource_ref: demo.my_action
    policy_type: action.concurrency
    parameters:
        threshold: 10

The ``action.concurrency.attr`` policy limits the executions for the action by input arguments. Let's say ``demo.my_remote_action`` has an input argument defined called ``hostname``. This is the name of the host where the remote command or script runs. By using the policy type ``action.concurrency.attr`` and specifying ``hostname`` as one of the attributes in the policy, only a number of ``demo.my_remote_action`` up to the defined threshold can run simultaneously on a given remote host.

.. sourcecode:: YAML

    name: my_remote_action.concurrency
    description: Limits the concurrent executions for my action.
    enabled: true
    resource_ref: demo.my_remote_action
    policy_type: action.concurrency
    parameters:
        threshold: 10
        attributes:
            - hostname

.. note::

    The concurrency policy type is not enabled by default and requires a backend service such as ZooKeeper or Redis to work.

Let's assume ZooKeeper or Redis is running on the same network where |st2| is installed. To enable the concurrency policy type in |st2|, provide the url to connect to the backend service in the coordination section of ``/etc/st2/st2.conf``. The following are examples for ZooKeeper and Redis.

Configuration example for ZooKeeper. ::

    [coordination]
    url = kazoo://username:password@host:port


Configuration example for Redis. ::

    [coordination]
    url = redis://username:password@host:port

Retry
-----

Retry policy (``actions.retry``) allows you to automatically retry (re-run) an action when a
particular failure condition is met. Right now we support retrying actions which have failed or
timed out.

The example below shows how to automatically retry ``core.http`` action for up to two times if it
times out.

.. literalinclude:: /../../contrib/hello-st2/policies/retry_core_http_on_timeout.yaml

Keep in mind that retrying an execution results in a new execution which shares all the attributes
from the retried execution (parameters, context, etc).
