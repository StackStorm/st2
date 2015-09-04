Integration Packs
===================

What is a Pack?
---------------
Pack is the unit of deployment for integrations and automations in order to extend |st2|. Typically a pack is organized along service or product boundaries e.g. AWS, Docker, Sensu etc. A pack can contain :doc:`Actions </actions>`, :doc:`Workflows </workflows>`,
:doc:`Rules </rules>`, :doc:`Sensors </sensors>`.

It is best to view a pack as the means to extend |st2| and allow it to integrate with an external systems. See `next section` to learn more about pack management.

Packs location and discovery
----------------------------

When using |st2| and pack management actions, all the packs are by default installed into the
system packs directory which defaults to ``/opt/stackstorm/packs``.

When |st2| searches for all the available packs it looks into the system packs directory and
into any additional directories which are specified in the ``packs_base_paths`` setting.

If user wants |st2| to look for packs in additional directories, they can do that by setting the
value of ``packs_base_paths`` in ``st2.conf`` (typically in :github_st2:`/etc/st2/st2.conf
</conf/st2.prod.conf>`, as described in :doc:`Configuration <config/config>`). The value must be a
colon delimited string of directory paths.

For example:

::

    [content]
    packs_base_paths=/home/myuser1/packs:/home/myuser2/packs

Note: Directories are always searched from left to right in the order they are
specified, with the system packs directory always being searched first.

Getting a pack
--------------

Pack management is done by |st2| actions from `packs` pack, pun intended. Run ``st2 action list --pack packs`` for a list of pack management actions.

Some packs can be installed and run "as is" without any configurations.

.. code-block:: bash

    st2 run packs.install packs=docker,sensu repo_url=https://github.com/StackStorm/st2contrib.git

This downloads the Sensu and Docker packs from the `StackStorm/st2contrib community repo on GitHub <https://github.com/StackStorm/st2contrib>`__ , places them as local content under ``/opt/stackstorm/packs``, registers with |st2| and loads the content.

By default packs are installed from the |st2| community repo. Use ``repo_url`` parameter to install a pack from a fork of `st2contrib`_, or from a custom repo. The following example installs all the packs from `StackStorm/st2incubator <https://github.com/StackStorm/st2contrib>`__ - the repo where you find our experiments and work-in-progress:

.. code-block:: bash

    st2 run packs.install register=all repo_url=https://github.com/StackStorm/st2incubator.git

To uninstall packs: ``st2 run packs.uninstall packs=docker,sensu``. This unloads and unregisters the content and deletes the packs from the disk.

The integration packs often require configurations to adjust to the environment. e.g. you will need to specify SMTP server for email, a puppet master URL for Puppet, or a Keystone endpoint and tenant credentials for OpenStack. The installation process is:

1. Download the pack with ``packs.download``
2. Check out the `REAMDE.md`. Adjust configurations per your environment.
3. Run pack setup via ``packs.setup_virtualenv``. It sets up virtual environment and installs the dependencies listed in requirements.txt.
4. Load the pack into |st2| with ``pack.load register=all|actions|rules|sensors``.

Let's install the Docker pack:

.. code-block:: bash

    # Download Docker pack from http://github.com/stackstorm/st2contrib
    st2 run packs.download packs=docker

    # Set up a virtual environment for this pack and installs all the pack dependencies
    # listed in requirements.txt (if any).
    # Virtual environment provides isolated Python environment for sensors and Python runner
    # actions.
    st2 run packs.setup_virtualenv packs=docker

    # Check out README.md and if necessary, adjust configuration for your environment
    less /opt/stackstorm/packs/docker/README.md

    # Load ALL the content: actions, sensors, rules
    # If you don't want to load sample rules by default, do
    # st2 run packs.load register=sensors && st2 run packs.load register=actions
    st2 run packs.load register=all

    # To pick up sensors, need to bounce the st2sensorcontainer process.
    # Note: live update coming soon and this won't be needed.
    st2 run packs.restart_component servicename=st2sensorcontainer

    # Verify that the docker pack was installed
    st2 action list --pack=docker
    st2 sensor list --pack=docker
    st2 trigger list --pack=docker

The docker pack is now installed and ready to use.

Packs may contain automations - rules and workflows. Rules are not loaded by default - you may want to review and adjust them before loading. Pass ``register=all`` option to ``packs.install`` and ``packs.load`` actions to get the rules loaded. Use `st2clt reload` for fine control - packs.load is an st2 action wrapper around it.

.. note:: Pack management is implemented as a pack of st2 actions. Check out :github_st2:`/opt/stackstorm/packs </contrib/packs>` for examples of defining actions and workflows.

Creating a Pack
---------------

See :doc:`/reference/packs` for details on how to pack your integrations and automations in a pack, how to publish it, and how to contribute it to the StackStorm community.

.. rubric:: What's Next?

* Explore existing packs from `StackStorm community <http:://www.stackstorm.com/community/>`__:

    - `st2contrib`_ - ready-to-use integration packs to many common products and tools.
    - `st2incubator`_ - upcoming integration packs and productivity tools.
* Learn how to write a pack and contribute to community  - :doc:`/reference/packs`
* Learn how to write :ref:`custom sensors <ref-sensors-authoring-a-sensor>` and :ref:`custom actions <ref-actions-writing-custom>`
* Check out `tutorials on stackstorm.com <http://stackstorm.com/category/tutorials/>`__ - a growing set of practical examples of automating with StackStorm.

.. include:: /engage.rst
