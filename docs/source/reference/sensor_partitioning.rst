Partitioning Sensors
====================

Often it is desirable to partition sensors across multiple sensor nodes. To this end
StackStorm offers a few approaches to defining partition schemes.

Each sensor node is identified by a name. The sensor nodename can be provided via a config
property `sensor_node_name` as follows:

::

    [sensorcontainer]
    ...
    sensor_node_name = sensornode1


1. Default
~~~~~~~~~~

In the default scheme all sensors are run on a particular node. As the name suggests it is
default scheme which ships out of the box. It is useful in cases where there is a single
sensor node.

No change required in the config file but for complete-ness the config would be as follows:

::

    [sensorcontainer]
    ...
    sensor_node_name = sensornode1
    partition_provider = name:default


2. Key-Value Store
~~~~~~~~~~~~~~~~~~

In this scheme the partition map is stored in the key-value store under a special sensor
node name scoped key. This is a way to provide a fixed map and does not help with any
dynamic mapping of sensors to sensor nodes.

::

    [sensorcontainer]
    ...
    sensor_node_name = sensornode1
    partition_provider = name:kvstore


To update the key value store use the following command:

::

    st2 key set sensornode1.sensor_partition "examples.SimpleSensor, examples.SimplePollingSensor"


Here the key name is of the format `{sensor_node_name}.sensor_partition`

3. File
~~~~~~~

In this scheme the partition map is stored in a file. This is a way to provide a fixed map and
does not help with any dynamic mapping of sensors to sensor nodes.

::

    [sensorcontainer]
    ...
    sensor_node_name = sensornode1
    partition_provider = name:file, partition_file:/etc/st2/partition_file.yaml


File content is as follows:

::

    # /etc/st2/partition_file.yaml
    ---
    sensornode1:
        - examples.SimplePollingSensor
        - examples.SimpleSensor


Note that the key is of the format `{sensor_node_name}.sensor_partition`

