Integration Packs
===================

What is a pack?
---------------
Pack is the unit of deployment for integrations and automations in order to extend st2. Typically a pack is organized along service or product boundaries e.g. AWS, Docker, Sensu etc. A pack can contain the following artifacts.

* `Actions </actions>`__
* `Workflows </workflows>`__
* `Rules </rules>`__
* `Sensors </sensors>`__

Its is best to view a pack as the means to extend st2 and allow it to integrate with external systems. See `next section </packs.html#getting-a-pack>`__ to learn more about pack management.

Getting a pack
--------------
Pack management is done by st2 actions from `packs` pack, pun intended. Run ``st2 action list --pack packs`` for a list of pack management actions.

Some packs can be installed and run "as is" without any configurations.

.. code-block:: bash

    st2 run packs.install packs=docker,sensu repo_url=https://github.com/StackStorm/st2contrib.git


This download the Sensu and Docker packs from the `StackStorm community repo <https://github.com/StackStorm/st2contrib>`__ on GitHub, places it into local content under ``/opt/stackstorm``, registers with st2 and loads the content.

By default they are installed from StackStorm community repo. Use ``repo_url`` parameter to install a pack from a fork of st2contrib, or from a custom repo. The repo is expected to have a top level ``packs`` directory.

To uninstall packs: ``st2 run packs.uninstall packs=docker,sensu``. This unloads and unregisters the content and deletes the packs from the disk.

The integration packs often require configurations to adjust to the environment. You will need to specify SMTP server for email, a puppet master URL for Puppet, or a Keystone endpoint and tenatn credentials for OpenStack. The installation process is:

1. Download the pack with ``packs.dowload``
2. Check out the `REAMDE.md`. Adjust configurations to your environment, install dependencies if needed.
3. Load the pack to StackStorm with ``pack.load``. Sometimes components may need a restart with ``pack.restart_component`` (live reload without restart is coming soon ).

Let's intall the Docker pack:

.. code-block:: bash

    # Download Docker pack from http://github.com/stackstorm/st2contrib
    st2 run packs.download packs=docker

    # Check out README.md.
    less /opt/stackstorm/docker/README.md

    # Apparently the pack needs docker-py python library. Installing...
    sudo pip install docker-py

    # Reloads the content
    st2 run packs.load

    # To pick up sensors, need to bounce the sensor_container.
    # Note: live update coming soon and this won't be needed.
    st2 run packs.restart_component servicename=sensor_container

    # Check that the docker got installed
    st2 action list --pack=docker
    st2 trigger list --pack=docker

The docker pack is now installed and ready to use.

Packs may contain automations - rules and workflows. Rules are not loaded by default - you may want to review and adjust them before loading. Pass ``register=rules`` option to ``packs.install`` and ``packs.load`` actions to get the rules loaded.

.. note:: Pack management is implemented as a pack of st2 actions. Explore :github_st2:`/opt/stackstorm/packs </contrib/packs>` for example of defining actions and workflows.

Create a pack
-------------
Packs have a defined structure that is prescribed by st2. It is required to follow this structure while creating your own pack and is also helpful to know while debugging issues with packs.

Anatomy
~~~~~~~
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

* ``etc`` - A folder to place bootstrap, dependency listings (like requirements.txt) etc. This folder is opaque to st2.
* ``pack.yaml`` - Manifest file which for now is only a sentinel file to identify the folder as a pack.
* ``config.yaml`` - Shared config file that is provided to both actions and sensors.

.. code-block:: bash

   # contents of actions/
   actions/
      lib/
      action1.json
      action1.py
      action2.json
      action1.sh
      workflow1.json
      workflow1.yaml

The ``actions`` folder contains action script files and action metadata files. See `Actions </actions>`__ and `Workflows </workflows>`__ for specifics on writing actions. Note that the ``lib`` sub-folder is always available for access for an action script.

.. code-block:: bash

   # contents of rules/
   rules/
      rule1.json
      rule2.json

The ``rules`` folder contains rules. See `Rules </rules>`__ for specifics on writing rules.

.. code-block:: bash

   # contents of sensors/
   sensors/
      common/
      sensor1.py
      sensor2.py

The ``sensors`` folder contains sensors. See `Sensors </Sensors>`__ for specifics on writing sensors and registering TriggerTypes.

Pushing a Pack to the Community
-------------------------------

.. todo:: Describe the process of contribution. Clone the "sample" repo? Or clone the st2contrib, submit a pull request. Or if you prefer to keep it separate, just let us know and we will reference it from the community site.

.. rubric:: What's Next?

* Connect your monitoring - install Sensu or Nagios pack
* Learn how to write custom sensors and actions - TBD

.. include:: engage.rst

