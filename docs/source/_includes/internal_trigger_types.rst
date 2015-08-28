.. NOTE: This file has been generated automatically, don't manually edit it

Action
~~~~~~

+---------------------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------+
| Reference                 | Description                                                  | Properties                                                                               |
+===========================+==============================================================+==========================================================================================+
| st2.generic.actiontrigger | Trigger encapsulating the completion of an action execution. | status, start_timestamp, parameters, action_name, result, execution_id                   |
+---------------------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------+
| st2.generic.notifytrigger | Notification trigger.                                        | status, start_timestamp, channel, action_ref, data, message, execution_id, end_timestamp |
+---------------------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------+
| st2.action.file_writen    | Trigger encapsulating action file being written on disk.     | content, host_info, ref, file_path                                                       |
+---------------------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------+

Key Value Pair
~~~~~~~~~~~~~~

+---------------------------------+---------------------------------------------------------+------------------------+
| Reference                       | Description                                             | Properties             |
+=================================+=========================================================+========================+
| st2.key_value_pair.create       | Trigger encapsulating datastore item creation.          | object                 |
+---------------------------------+---------------------------------------------------------+------------------------+
| st2.key_value_pair.update       | Trigger encapsulating datastore set action.             | object                 |
+---------------------------------+---------------------------------------------------------+------------------------+
| st2.key_value_pair.value_change | Trigger encapsulating a change of datastore item value. | new_object, old_object |
+---------------------------------+---------------------------------------------------------+------------------------+
| st2.key_value_pair.delete       | Trigger encapsulating datastore item deletion.          | object                 |
+---------------------------------+---------------------------------------------------------+------------------------+

Sensor
~~~~~~

+--------------------------+--------------------------------------------------+------------+
| Reference                | Description                                      | Properties |
+==========================+==================================================+============+
| st2.sensor.process_spawn | Trigger indicating sensor process is started up. | object     |
+--------------------------+--------------------------------------------------+------------+
| st2.sensor.process_exit  | Trigger indicating sensor process is stopped.    | object     |
+--------------------------+--------------------------------------------------+------------+
