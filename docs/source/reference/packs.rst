Create and Contribute a Pack
=============================

Packs have a defined structure that is prescribed by |st2|. It is required to follow this structure while creating your own pack and is also helpful to know while debugging issues with packs.

Anatomy
-------
Canonical pack as laid out on the file system.

.. code-block:: bash

   # contents a pack folder
   actions/
   rules/
   sensors/
   etc/
   config.yaml
   pack.yaml

At the topmost level are the main folders ``actions``, ``rules`` and ``sensors`` as well as some shared files.

* ``etc`` - A folder to place bootstrap, dependency listings (like requirements.txt) etc. This folder is opaque to |st2|.
* ``pack.yaml`` - Manifest file which for now is only a sentinel file to identify the folder as a pack.
* ``config.yaml`` - Shared config file that is provided to both actions and sensors.

.. code-block:: bash

   # contents of actions/
   actions/
      lib/
      action1.yaml
      action1.py
      action2.yaml
      action1.sh
      workflow1.yaml
      workflow2.yaml

The ``actions`` folder contains action script files and action metadata files. See :doc:`Actions </actions>` and :doc:`Workflows </workflows>` for specifics on writing actions. Note that the ``lib`` sub-folder is always available for access for an action script.

.. code-block:: bash

   # contents of rules/
   rules/
      rule1.yaml
      rule2.yaml

The ``rules`` folder contains rules. See :doc:`Rules </rules>` for specifics on writing rules.

.. code-block:: bash

   # contents of sensors/
   sensors/
      common/
      sensor1.py
      sensor2.py

The ``sensors`` folder contains sensors. See :doc:`Sensors </sensors>` for specifics on writing sensors and registering TriggerTypes.

My first pack
-------------
If you would like to create a pack yourself then follow these *simple* steps.

1. Create a pack folder and its internal structure

.. code-block:: bash

   # Name of folder is name of the pack. Therefore, this is the 'hello-|st2|' pack.
   mkdir hello-st2
   cd hello-st2
   mkdir actions
   mkdir rules
   mkdir sensors
   mkdir etc

Note that all folders are optional. If a folder is present it is introspected for content i.e. it is safe to skip a folder or keep it empty.

2. Now create the pack description files.

.. code-block:: bash

   # Name of folder is name of the pack. Therefore, this is the 'hello-st2' pack.
   touch pack.yaml
   touch config.yaml

Lets leave these empty for now and fill them in as per requirement.

3. Add an action

.. code-block:: bash

   touch actions/hello.yaml
   touch actions/hello.sh

   # Content of hello.sh
   #!/usr/bin/env bash
   echo "Hello st2!"

   # Content of hello.yaml
   ---
       name: "hello"
       runner_type: "run-local"
       description: "Hello st2 action."
       enabled: true
       entry_point: "hello.sh"
       parameters: {}

4. Add a sensor

.. code-block:: bash

    touch sensors/sensor1.py

    # content of sensor1.py
    import eventlet

    class HelloSensor(object):
        def __init__(self, container_service, config=None):
            self._container_service = container_service
            self._stop = False

        def setup(self):
            pass

        def start(self):
            eventlet.spawn_after(self._on_time, 10)

        def stop(self):
            self._stop = True

        def get_trigger_types(self):
            return [{
                'name': 'event1',
                'payload_schema': {
                    'type': 'object'
                }
            }]

        def _on_time(self):
            if self._stop:
                return
            self._do_post_trigger()
            eventlet.spawn_after(self._on_time, 10)

        def _do_post_trigger(self):
            trigger = {'trigger': 'hello-st2.event1'}
            self._container_service.dispatch(trigger, {})


    # Methods required for programmable sensors.
    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass

5. Add a rule

.. code-block:: bash

   touch rules/rule1.yaml

   # Content of rule1.yaml
   ---
       name: "on_event1"
       description: "Sample rule firing on hello-st2.event1."

       trigger:
           type: "hello-st2.event1

       action:
           ref: "hello-st2.hello"
           parameters: {}

       enabled: true

6. Deploy pack manually

.. code-block:: bash

   # Assuming that hello-st2 is on the same machine as the |st2| content-repo.
   cp -R ./hello-st2 /opt/stackstorm/packs

   # Reloads the content
   st2 run packs.load register=all

   # To pick up sensors, need to bounce the sensor_container.
   # Note: live update coming soon and this won't be needed.
   st2 run packs.restart_component servicename=sensor_container


Once you follow steps 1-6 you will have created your first pack. Commands like ``st2 action list``, ``st2 rule list`` and ``st2 trigger list`` will show you the loaded content.

Next steps would be to create an integration pack for you favorite tool or service that you would like to use with |st2|. Happy hacking!


Pushing a Pack to the Community
-------------------------------

"What's better than getting to use your mega-awesome |st2| pack?" Why publishing it to the community and sharing your awesomeness with others. For this purpose we have created the `StackStorm community repo <https://github.com/StackStorm/st2contrib>`__ where you can share and pull other content packs. Submit a pull request! Here are the steps:


1. Clone the |st2| community repo locally

.. code-block:: bash

   git clone https://github.com/StackStorm/st2contrib.git

2. Put your pack in the repo

.. code-block:: bash

   cd st2contrib
   cp -R ~/hello-st2 ./packs/

3. Create a local commit and push to remote repo.

.. code-block:: bash

   # Creating a local branch new/hello-st2
   git checkout -b new/hello-st2
   git add packs/hello-st2
   git commit -m "My first pack."
   git push origin new/hello-st2

4. Create pull request

    * Goto `StackStorm community repo <https://github.com/StackStorm/st2contrib>`__. You will see a yellow banner with a button ``Compare & Pull request``. Click the button.
    * Fill in details describing the pack. Click the ``Create pull request`` button.
    * Github will notify us of a new pull request(PR) and we shall review the code, make sure everything looks pristine and merge it in to make your pack publicly available via st2contrib.

.. hint:: If you are new to git/GitHub, `here <https://try.github.io/levels/1/challenges/1>`__ is an excellent interactive learning resource.

Contributors License Agreement
--------------------------------
By contributing you agree that these contributions are your own (or approved by your employer) and you grant a full, complete, irrevocable copyright license to all users and developers of the project, present and future, pursuant to the license of the project.

-------------

.. include:: ../engage.rst
