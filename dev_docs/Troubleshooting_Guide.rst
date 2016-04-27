Troubleshooting Guide
=====================

**Q: After starting st2 server using** ``tools/launchdev.sh`` **script, getting following error:**::

  $ st2 action list
  ERROR: HTTPConnectionPool(host='127.0.0.1', port=9101): Max retries exceeded with url: /v1/actions
  (Caused by NewConnectionError( <requests.packages.urllib3.connection.HTTPConnection object at
  0x7fced578fbd0>: Failed to establish a new connection: [Errno 111] Connection refused',))

**How to fix this ?**


**A:** First lets find out what is causing this:

*Diagnosis:*

- As the output shows we are unable to establish new connection using port 9101. Let us find which ports are used:

.. code:: bash

  $ sudo netstat -tupln | grep 910
  tcp     0    0 0.0.0.0:9100    0.0.0.0:*   LISTEN  32420/python
  tcp     0    0 0.0.0.0:9102    0.0.0.0:*   LISTEN  32403/python
  
As we can see from above output port ``9101`` is not even up. To verify this let us try another command:

.. code:: bash

  $ ps auxww | grep st2 | grep 910
  vagrant  32420  0.2  1.5  79228 31364 pts/10   Ss+  18:27   0:00 /home/vagrant/git/st2/virtualenv/bin/python
  ./virtualenv/bin/gunicorn_pecan ./st2auth/st2auth/gunicorn_config.py -k eventlet -b 0.0.0.0:9100 --workers 1
  vagrant@ether git/st2 (master %) » ps auxww | grep st2 | grep 32403  
  vagrant  32403  0.2  1.5  79228 31364 pts/3    Ss+  18:27   0:00 /home/vagrant/git/st2/virtualenv/bin/python
  ./virtualenv/bin/gunicorn_pecan ./st2stream/st2stream/gunicorn_config.py -k eventlet -b 0.0.0.0:9102 --workers 1
  
- This suggests that the API process crashed, we can verify that by running ``screen -ls``.::

.. code:: bash

  $ screen -ls
    There are screens on:
	 15781.st2-auth	(04/26/2016 06:39:10 PM)	(Detached)
	 15778.st2-notifier	(04/26/2016 06:39:10 PM)	(Detached)
	 15767.st2-sensorcontainer	(04/26/2016 06:39:10 PM)	(Detached)
	 15762.st2-stream	(04/26/2016 06:39:10 PM)	(Detached)
    3 Sockets in /var/run/screen/S-vagrant.
 
- Now let us check the logs for any errors: 

.. code:: bash

  tail logs/st2api.log
  2016-04-26 18:27:15,603 140317722756912 AUDIT triggers [-] Trigger updated. Trigger.id=570e9704909a5030cf758e6d 
  (trigger_db={'description': None, 'parameters': {}, 'ref_count': 0, 'name': u'st2.sensor.process_exit', 
  'uid': u'trigger:core:st2.sensor.process_exit:5f02f0889301fd7be1ac972c11bf3e7d', 'type': u'core.st2.sensor.process_exit', 
  'id': '570e9704909a5030cf758e6d', 'pack': u'core'})
  2016-04-26 18:27:15,603 140317722756912 AUDIT triggers [-] Trigger created for parameter-less TriggerType. 
  Trigger.id=570e9704909a5030cf758e6d (trigger_db={'description': None, 'parameters': {}, 'ref_count': 0, 
  'name': u'st2.sensor.process_exit', 'uid': u'trigger:core:st2.sensor.process_exit:5f02f0889301fd7be1ac972c11bf3e7d', 
  'type': u'core.st2.sensor.process_exit', 'id': '570e9704909a5030cf758e6d', 'pack': u'core'})
  2016-04-26 18:27:15,605 140317722756912 DEBUG base [-] Conflict while trying to save in DB.
  Traceback (most recent call last):
  File "/home/vagrant/git/st2/st2common/st2common/persistence/base.py", line 120, in insert
    model_object = cls._get_impl().insert(model_object)
  File "/home/vagrant/git/st2/st2common/st2common/models/db/__init__.py", line 207, in insert
    instance = self.model.objects.insert(instance)
  File "/home/vagrant/git/st2/virtualenv/local/lib/python2.7/site-packages/mongoengine/queryset/base.py", line 307, in insert
    raise NotUniqueError(message % unicode(err))
  NotUniqueError: Could not save document (E11000 duplicate key error index: st2.role_d_b.$name_1 dup key: { : "admin" })
  2016-04-26 18:27:15,606 140317722756912 DEBUG base [-] Conflict while trying to save in DB.
  Traceback (most recent call last):
    File "/home/vagrant/git/st2/st2common/st2common/persistence/base.py", line 120, in insert
    model_object = cls._get_impl().insert(model_object)
  File "/home/vagrant/git/st2/st2common/st2common/models/db/__init__.py", line 207, in insert
    instance = self.model.objects.insert(instance)
  File "/home/vagrant/git/st2/virtualenv/local/lib/python2.7/site-packages/mongoengine/queryset/base.py", line 307, in insert
    raise NotUniqueError(message % unicode(err))
  NotUniqueError: Could not save document (E11000 duplicate key error index: st2.role_d_b.$name_1 dup key: { : "observer" })
  2016-04-26 18:27:15,607 140317722756912 DEBUG base [-] Conflict while trying to save in DB.
  Traceback (most recent call last):
    File "/home/vagrant/git/st2/st2common/st2common/persistence/base.py", line 120, in insert
      model_object = cls._get_impl().insert(model_object)
    File "/home/vagrant/git/st2/st2common/st2common/models/db/__init__.py", line 207, in insert
     instance = self.model.objects.insert(instance)
    File "/home/vagrant/git/st2/virtualenv/local/lib/python2.7/site-packages/mongoengine/queryset/base.py", line 307, in insert
      raise NotUniqueError(message % unicode(err))
  NotUniqueError: Could not save document (E11000 duplicate key error index: st2.role_d_b.$name_1 dup key: { : "system_admin" })
  2016-04-26 18:27:15,676 140317722756912 INFO driver [-] Generating grammar tables from /usr/lib/python2.7/lib2to3/Grammar.txt
  2016-04-26 18:27:15,693 140317722756912 INFO driver [-] Generating grammar tables from /usr/lib/python2.7/lib2to3/PatternGrammar.txt
  
- To figure out whats wrong let us dig down further. Activate the virtualenv in st2 and run following command :

.. code:: bash

   (virtualenv) $ ST2_CONFIG_PATH=conf/st2.dev.conf ./virtualenv/bin/gunicorn_pecan ./st2api/st2api/gunicorn_config.py -k eventlet -b 0.0.0.0:9101 --workers 1

The above mentioned command will give out logs, we may find some error in the end of logs like this:

.. code:: bash

    File "/home/vagrant/git/st2/st2common/st2common/models/api/keyvalue.py", line 19, in <module>
      from keyczar.keys import AesKey
  ImportError: No module named keyczar.keys
  
So the problem is : module keyczar is missing. This module can be downloaded using following command:

*Solution:*

.. code:: bash

  (virtualenv) $ pip install python-keyczar
  

This should fix the issue. Now deactivate the virtual env and run ``tools/launchdev.sh restart``

