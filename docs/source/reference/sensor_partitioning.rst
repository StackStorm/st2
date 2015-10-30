Partitioning Sensors
====================

Often it is desirable to partition sensors across multiple sensor nodes. To this end
StackStorm offers a few approaches to defining partition schemes.

Each sensor node is identified by a name. The sensor nodename can be provided via a config
property `sensor_node_name` as follows:

::

    [sensorcontainer]
    ...
    sensor_node_name = sensornode.example.net_f7aeb3ed


1. Default
~~~~~~~~~~

In the default scheme all sensors are run on a particular node. As the name suggests it is
default scheme which ships out of the box. It is useful in cases where there is a single
sensor node.

No change required in the config file but for complete-ness the config would be as follows:

::

    [sensorcontainer]
    ...
    sensor_node_name = sensornode.example.net_f7aeb3ed
    partition_provider = name:default


2. Key-Value Store
~~~~~~~~~~~~~~~~~~

In this scheme the partition map is stored in the key-value store under a special sensor
node name scoped key. This is a way to provide a fixed map and does not help with any
dynamic mapping of sensors to sensor nodes.

::

    [sensorcontainer]
    ...
    sensor_node_name = sensornode.example.net_f7aeb3ed
    partition_provider = name:kvstore


To update the key value store use the following command:

::

    st2 key set sensornode.example.net_f7aeb3ed.sensor_partition "examples.SampleSensor, examples.SamplePollingSensor"


Here the key name is of the format `{sensor_node_name}.sensor_partition`

3. File
~~~~~~~

In this scheme the partition map is stored in a file. This is a way to provide a fixed map and
does not help with any dynamic mapping of sensors to sensor nodes.

::

    [sensorcontainer]
    ...
    sensor_node_name = sensornode.example.net_f7aeb3ed
    partition_provider = name:file, partition_file:/etc/st2/partition_file.yaml


File content is as follows:

::

    # /etc/st2/partition_file.yaml
    ---
    sensornode.example.net_f7aeb3ed:
        - examples.SamplePollingSensor
        - examples.SampleSensor


Note that the key is of the format `{sensor_node_name}.sensor_partition`

4. Hash
~~~~~~~

This is a dynamic scheme where each sensor node is assigned one of more hash ranges. Each sensor itself
is hashed and depending on which bucket of the range it fits into a sensornode runs the sensor. Hash
schema is particulaly useful when there are a lot of sensors and fewer nodes typically characterized by
an order of magnitude difference.

A few special keys ``MIN`` and ``MAX`` can also be used. This is how a typical hash provider configuration
would look.


::

    [sensorcontainer]
    ...
    sensor_node_name = sensornode.example.net_f7aeb3ed
    partition_provider = name:hash, hash_ranges:0..1024|2048..4096

Notice the peculiar format of hash_ranges. A single sensor node can support multiple sub-ranges. Each sub-range
is of the form  ``{{RANGE_START}}..{{RANGE_END}}``. Multiple sub-range are combined using ``|``.

Some useful examples

* Full range - ``MIN..MAX`` or ``0..4294967296``
* First half of range - ``MIN..2147483648``
* Second half of range - ``2147483648..MAX``
* Multiple non-contiguous ranges - ``0..1024|2048..3072|2147483648..MAX``
