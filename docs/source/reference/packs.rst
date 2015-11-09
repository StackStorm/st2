Create and Contribute a Pack
=============================

Packs have a defined structure that is prescribed by |st2|. It is required to follow this structure while creating your own pack and is also helpful to know while debugging issues with packs.

Anatomy
-------
Canonical pack as laid out on the file system.

.. code-block:: bash

   # contents of a pack folder
   actions/
   rules/
   sensors/
   aliases/
   policies/
   config.yaml
   pack.yaml
   requirements.txt

At the topmost level are the main folders ``actions``, ``rules``, ``sensors``, ``aliases`` and ``policies`` as well as some shared files.

* ``pack.yaml`` - Metadata file that describes and identifies the folder as a pack.
* ``config.yaml`` - Shared config file that is provided to both actions and sensors.
* ``requirements.txt`` - File containing a list of python dependencies.

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
      workflows/
        workflow1.yaml
        workflow2.yaml

The ``actions`` folder contains action script files and action metadata files. See :doc:`Actions </actions>` and :doc:`Workflows </workflows>` for specifics on writing actions. Since metadata files and workflow definitions can both be written as YAML, it's good practice to put the workflow definitions in a separate directory. Note that the ``lib`` sub-folder is always available for access for an action script.

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
      sensor1.yaml
      sensor2.py
      sensor2.yaml

The ``sensors`` folder contains sensors. See :doc:`Sensors </sensors>` for specifics on writing sensors and registering TriggerTypes.

.. code-block:: bash

   # contents of aliases/
   aliases/
      alias1.yaml
      alias2.yaml

The ``aliases`` folder contains Action Aliases. See :doc:`Action Alias </chatops/aliases>` for specifics on writing Action Aliases.

.. code-block:: bash

   # contents of policies/
   policies/
      policy1.yaml
      policy2.yaml

The ``policies`` folder contains Policies. See :doc:`Policies </policies>` for specifics on writing Policies.

My first pack
-------------
If you would like to create a pack yourself then follow these *simple* steps. In the example below, we will create a simple pack named **hello-st2**. The full example is also available at :github_st2:`st2/contrib/hello-st2 </contrib/hello-st2>`.

1. First, let's create the pack folder structure and related files. Let's keep the metadata files such as pack.yaml, config.yaml, and requirements.txt empty for now.

.. code-block:: bash

   # Use the name of the pack for the folder name.
   mkdir hello-st2
   cd hello-st2
   mkdir actions
   mkdir rules
   mkdir sensors
   mkdir aliases
   mkdir policies
   touch pack.yaml
   touch config.yaml
   touch requirements.txt

.. note::
    All folders are optional. If a folder is present, it is introspected for content. So it is safe to skip a folder or keep it empty.

The contents of ``pack.yaml`` should be as under.

.. literalinclude:: /../../contrib/hello-st2/pack.yaml

2. Create the action. The following example simply echoes a greeting.

Copy the following content to actions/greet.yaml

.. literalinclude:: /../../contrib/hello-st2/actions/greet.yaml

Copy the following content to actions/greet.sh

.. literalinclude:: /../../contrib/hello-st2/actions/greet.sh

3. Create a sensor. The sample sensor below publishes an event to |st2| every 60 seconds.

Copy the following content to sensors/sensor1.yaml

.. literalinclude:: /../../contrib/hello-st2/sensors/sensor1.yaml

Copy the following content to sensors/sensor1.py

.. literalinclude:: /../../contrib/hello-st2/sensors/sensor1.py

4. Create a rule. The sample rule below is triggered by event from the sensor and invokes the action from the samples above.

Copy the following content to rules/rule1.yaml

.. literalinclude:: /../../contrib/hello-st2/rules/rule1.yaml

5. Create an action alias. The sample action alias below aliases the greet action and makes it accessible from ChatOps.

Copy the following content to aliases/alias1.yaml

.. literalinclude:: /../../contrib/hello-st2/aliases/alias1.yaml

6. Create a policy. The sample policy below limits concurrent operation of the greet action.

Copy the following content to policies/policy1.yaml

.. literalinclude:: /../../contrib/hello-st2/policies/policy1.yaml

7. Deploy this pack manually.

.. code-block:: bash

   # Assuming that hello-st2 is on the same machine where StackStorm is running.
   cp -R ./hello-st2 /opt/stackstorm/packs

   # Reloads the content
   st2 run packs.load register=all

Once you follow steps 1-7 you will have created your first pack. Commands like ``st2 action list``, ``st2 rule list`` and ``st2 trigger list`` will show you the loaded content. To check if the sensor triggering action is working, run ``st2 execution list``, there should be an entry for executing ``hello-st2.greet`` every minute.

Next steps would be to create an integration pack for you favorite tool or service that you would like to use with |st2|. Happy hacking!


Pushing a Pack to the Community
-------------------------------

So, now you forged this uber-awesome pack in |st2|, what's next? Do you want to share your awesome pack and knowledge with the community? For this purpose we have created the `StackStorm community repo <https://github.com/StackStorm/st2contrib>`__ where you can share and pull other content packs. Submit a pull request! Here are the steps:

1. Fork the |st2| community repository (st2contrib) on Github

  * Go to https://github.com/StackStorm/st2contrib and click "Fork" button on
    the right

2. Clone your fork

.. code-block:: bash

   git clone https://github.com/<your username>/st2contrib.git

3. Create a branch for your changes

.. code-block:: bash

    cd st2contrib
    git checkout -b my_uber_new_pack

4. Put your pack in the repo

.. code-block:: bash

   cp -R ~/uber_new_pack ./packs/

5. Create a local commit and push to remote repo

.. code-block:: bash

   git add packs/uber_new_pack
   git commit -m "Awesomeness!!!"
   git push origin my_uber_new_pack

4. Create pull request

  * Go to `StackStorm community repo <https://github.com/StackStorm/st2contrib>`__. You will see a yellow banner with a button ``Compare & Pull request``. Click the button.
  * Fill in details describing the pack. Click the ``Create pull request`` button.
  * Github will notify us of a new pull request (PR) and we shall review the code, make sure everything looks pristine and merge it in to make your pack publicly available via st2contrib.

.. hint:: If you are new to git/GitHub, `here <https://try.github.io/levels/1/challenges/1>`__ is an excellent interactive learning resource.

Contributors License Agreement
--------------------------------
By contributing you agree that these contributions are your own (or approved by your employer) and you grant a full, complete, irrevocable copyright license to all users and developers of the project, present and future, pursuant to the license of the project.

-------------

.. include:: ../engage.rst
