Mistral + YAQL
==============
YAQL is typically used for simple conditional evaulation and data transformation in Mistral 
workflows. There will be many cases where you did not author the actions but there's a need to 
decide from the result of the action whether to continue or there's a need to transform the 
result to another value or structure for the next action in the workflow.

Here are some examples of usages.

* Select values for a key from a list of dictionary.
* Filter the list where one or more fields match condition(s).
* Transform a list to dictionary or vice versa.
* Simple arithmetic.
* Evaluation of boolean logic.
* Any combination of select, filter, transform, and evaluate.

.. note::

    Please refer to offical OpenStack documentation for Mistral and YAQL. The documentation here
    is meant to help |st2| users get a quick start. 
    `YAQL unit tests <https://github.com/openstack/yaql/tree/master/yaql/tests>`_ are also a great
    source of reference on how to use and what features are supported in YAQL especially to cover
    gaps in OpenStack YAQL documentation.

Basics
++++++
The following are statements in the workflow and task definition that accepts YAQL. 

* task action input
* task concurrency
* task on-complete
* task on-error
* task on-success
* task pause-before
* task publish
* task retry break-on
* task retry continue-on
* task retry count
* task retry delay
* task timeout
* task wait-before
* task wait-after
* task with-items
* workflow output

Each of the statement can take a string with one or more YAQL expressions. Each expression in the 
string should be encapsulated with ``<% %>``. When evaluating a YAQL expression, Mistral also 
passes a JSON dictionary (aka context) to the YAQL engine. The context contains all the workflow
inputs, published variables, and result of completed tasks up to this point of workflow 
execution including the current task. The YAQL expression can refer to one or more variables in 
the context. The reserved symbol ``$`` is used to reference the context. For example, given the 
context ``{"ip": "127.0.0.1", "port": 8080}``, the string ``https://<% $.ip %>:<% $.port>/api`` 
returns ``https://127.0.0.1:8080/api``. The following is the same example used in a workflow.

.. code-block:: yaml

    version: '2.0'

    examples.yaql-basic:
        type: direct
        input:
            - ip
            - port
        tasks:
            task1:
                action: examples.call-api
                input:
                    endpoint: https://<% $.ip %>:<% $.port>/api

Certain statements in Mistral such as on-success and on-error can evaluate boolean logic. The 
``on-condition`` related statements are used for transition from one task to another. If a 
boolean logic is defined with these statements, it can be used to evaluate whether the transition
should continue or not. Complex boolean logic using a combination of ``not``, ``and``, ``or``, and
parentheses is possible. Take the following workflow as an example, execution of certain branch 
in the workflow depends on the value of ``$.path``. If ``$.path = a``, then task ``a`` is executed. 
If ``$.path = b``, then task ``b``. Finally task ``c`` is executed if neither.

.. literalinclude:: /../../contrib/examples/actions/workflows/mistral-branching.yaml

Dictionaries
++++++++++++
To create a dictionary, use the ``dict`` function. For example, ``<% dict(a=>123, b=>true) %>``
returns ``{'a': 123, 'b': True}``. Let's say this dictionary is published to the context as
``dict1``, the keys function returns ``<% $.dict1.keys() %>`` returns ``['a', 'b']`` and
``<% $.dict1.values() %>`` returns the values ``[123, true]``. Concatenating dictionaries
can be done as ``<% dict(a=>123, b=>true) + dict(c=>xyz) %>`` which returns
``{'a': 123, 'b': True, 'c': 'xyz'}``. Specific key-value pair can be accessed by key name
such as ``<% $.dict1.get(b) %>`` which returns ``True``. Given the alternative
``<% $.dict1.get(b, false) %>`` and lets say the key ``b`` does not exist, then ``False``
will be returned by default.

Lists
+++++
To create a list, use the ``list`` functions. For example, ``<% list(1, 2, 3) %>`` returns 
``[1, 2, 3]`` and ``<% list(abc, def) %>`` returns ``['abc', 'def']``. List concatenation  
can be done as ``<% list(abc, def) + list(ijk, xyz) %>`` which returns 
``['abc', 'def', 'ijk', 'xyz']``. Let's say this list is published to the context as ``list1``,
items can also be access via index such as ``<% $.list1[0] %>`` which returns ``abc``.

Queries
+++++++
Let's take the following context as an example.

.. code-block:: json

    {
        'vms': [
            {
                'name': 'vmweb1',
                'region': 'us-east',
                'role': 'web'
            },
            {
                'name': 'vmdb1',
                'region': 'us-east',
                'role': 'db'
            },
            {
                'name': 'vmweb2',
                'region': 'us-west',
                'role': 'web'
            },
            {
                'name': 'vmdb2',
                'region': 'us-west',
                'role': 'db'
            }
        ]
    }

The following YAQL expressions are some sample queries that YAQL is capable of.

* ``<% $.vms.select($.name) %>`` returns the list of VM names ``['vmweb1', 'vmdb1', 'vmweb2', 'vmdb2']``.
* ``<% $.vms.select([$.name, $.role]) %>`` returns a list of names and roles as ``[['vmweb1', 'web'], ['vmdb1', 'db'], ['vmweb2', 'web'], ['vmdb2', 'db']]``.
* ``<% $.vms.select($.region).distinct() %>`` returns the distinct list of regions ``['us-east', 'us-west']``.
* ``<% $.vms.where($.region = 'us-east').select($.name) %>`` selects only the VMs in us-east ``['vmweb1', 'vmdb1']``.
* ``<% $.vms.where($.region = 'us-east' and $.role = 'web').select($.name) %>`` selects only the web server in us-east ``['vmweb1']``.

List to Dictionary
++++++++++++++++++
Now there're cases when it's easier to work with dictionaries instead of list (i.e. random
access of a value with the key). Let's take the same list of VM records from above and convert
it to a dictionary where VM name is the key and the value is the record. YAQL can convert a list
of lists to a dictionary where each list contains the key and value. For example, the expression
``<% dict(vms=>dict($.vms.select([$.name, $]))) %>`` returns the following dictionary. In this
expression, we took the original ``vms`` list, return a list of ``[name, record]``, and then
convert it to a dictionary.

.. code-block:: json

    {
        'vms': {
            'vmweb1': {
                'name': 'vmweb1',
                'region': 'us-east',
                'role': 'web'
            },
            'vmdb1': {
                'name': 'vmdb1',
                'region': 'us-east',
                'role': 'db'
            },
            'vmweb2': {
                'name': 'vmweb2',
                'region': 'us-west',
                'role': 'web'
            },
            'vmdb2': {
                'name': 'vmdb2',
                'region': 'us-west',
                'role': 'db'
            }
        ]
    }

Other YAQL Functions
++++++++++++++++++++
YAQL has a list of built-in functions to work with strings, dictionaries, lists, and etc. Some
of these are pass thru to python built-in functions (i.e. int, float, pow, regex, round, etc.).
Mistral includes additional workflow related functions to the list. For example, the call to
function ``<% len(foobar) %>`` to get the length of the string ``foobar`` returns the value
``6``. The following is a curated list of commonly used functions. Please visit the YAQL
documentation and git repo to explore more options.

**Built-in**

* ``float(value)`` converts value to float.
* ``int(value)`` converts value to integer.
* ``len(list)`` and ``len(string)`` returns the length of the list and string respectively. 
* ``max(a, b)`` returns the larger value between a and b.
* ``min(a, b)`` returns the smaller value between a and b.
* ``regex(expression).match(pattern)`` returns True if expression matches pattern.
* ``regex(expresssion).search(pattern)`` returns first instance that matches pattern.
* ``'some string'.toUpper()`` converts the string to all upper cases.
* ``'some string'.toLower()`` converts the string to all lower cases.
* ``['some', 'list'].contains(value)`` returns True if list contains value. 

**Mistral**

* ``env()`` returns the environment variables passed to the workflow execution on invocation.
* ``task(task_name)`` returns the state, state_info, and result of task given task_name.
