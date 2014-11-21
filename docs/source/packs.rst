Integration Packs
===================

What is a Pack?
---------------
Pack is the unit of deployment for integrations and automations in order to extend |st2|. Typically a pack is organized along service or product boundaries e.g. AWS, Docker, Sensu etc. A pack can contain :doc:`Actions </actions>`, :doc:`Workflows </workflows>`,
:doc:`Rules </rules>`, :doc:`Sensors </sensors>`.

It is best to view a pack as the means to extend |st2| and allow it to integrate with an external systems. See `next section` to learn more about pack management.

Getting a pack
--------------
Pack management is done by |st2| actions from `packs` pack, pun intended. Run ``st2 action list --pack packs`` for a list of pack management actions.

Some packs can be installed and run "as is" without any configurations.

.. code-block:: bash

    st2 run packs.install packs=docker,sensu repo_url=https://github.com/StackStorm/st2contrib.git

This downloads the Sensu and Docker packs from the `StackStorm community repo on GitHub <https://github.com/StackStorm/st2contrib>`__ , places them as local content under ``/opt/stackstorm/packs``, registers with |st2| and loads the content.

By default packs are installed from the |st2| community repo. Use ``repo_url`` parameter to install a pack from a fork of st2contrib, or from a custom repo. If using a custom repo make sure to place packs a top level ``packs`` directory.

To uninstall packs: ``st2 run packs.uninstall packs=docker,sensu``. This unloads and unregisters the content and deletes the packs from the disk.

The integration packs often require configurations to adjust to the environment. e.g. you will need to specify SMTP server for email, a puppet master URL for Puppet, or a Keystone endpoint and tenant credentials for OpenStack. The installation process is:

1. Download the pack with ``packs.download``
2. Check out the `REAMDE.md`. Adjust configurations per your environment, install dependencies if needed.
3. Load the pack into |st2| with ``pack.load``. Sometimes components may need a restart with ``pack.restart_component`` (live reload without restart is coming soon).

Let's install the Docker pack:

.. code-block:: bash

    # Download Docker pack from http://github.com/stackstorm/st2contrib
    st2 run packs.download packs=docker

    # Check out README.md.
    less /opt/stackstorm/packs/docker/README.md

    # Apparently the pack needs docker-py python library. Installing...
    sudo pip install docker-py

    # Reloads the content
    st2 run packs.load

    # To pick up sensors, need to bounce the sensor_container.
    # Note: live update coming soon and this won't be needed.
    st2 run packs.restart_component servicename=sensor_container

    # Verify that the docker pack was installed
    st2 action list --pack=docker
    st2 trigger list --pack=docker

The docker pack is now installed and ready to use.

Packs may contain automations - rules and workflows. Rules are not loaded by default - you may want to review and adjust them before loading. Pass ``register=rules`` option to ``packs.install`` and ``packs.load`` actions to get the rules loaded.

.. note:: Pack management is implemented as a pack of st2 actions. Check out :github_st2:`/opt/stackstorm/packs </contrib/packs>` for examples of defining actions and workflows.

Creating a Pack
---------------

See :doc:`/reference/packs` for details on how to pack your integrations and automations in a pack, how to publish it, and how to contribute it to the StackStorm community.

.. rubric:: What's Next?

* Learn how to write a pack and contribute to community  - :doc:`/reference/packs`
* Learn how to write :ref:`custom sensors <ref-sensors-authoring-a-sensor>` and :ref:`custom actions <ref-actions-writing-custom>`
* Explore the `StackStorm community <http:://www.stackstorm.com/community/>`__

.. include:: /engage.rst
