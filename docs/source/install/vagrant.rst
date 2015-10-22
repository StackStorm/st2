Vagrant
=================

|st2| provides pre-built Vagrant boxes for both `VirtualBox <https://www.virtualbox.org>` and `VMWare <https://www.vmware.com>` providers. By default, the setup will install the lastest stable release of |st2|. These boxes are hosted on the `Hashicorp Atlas <https://atlas.hashicorp.com/stackstorm/boxes/st2>` website.

Using these vagrant images, it is possible to setup:

* Spin up a test environment to play with StackStorm (`st2`)
* Spin up a development environment to work with StackStorm (`st2dev`)
* Begin building infrastructure patterns using pre-configured Config Management tools

Getting Started
---------------

::

   git clone https://github.com/StackStorm/st2workroom.git st2workroom
   cd st2workroom
   vagrant up st2


If you have previously used deployed |st2| and downloaded the st2express box it might be a good idea to update the box. If this is your absolute first install of |st2| then skip this step.

::

  vagrant box update st2


This will boot up a fresh |st2| installation along with the Mistral workflow engine on Ubuntu 14.04 LTS. While loading, some console output in red is expected and can be safely ignored. Once completed, you will see the following console output.

.. include:: /_includes/install/ok.rst

Visit the setup URL output on your command line by entering the address in your web browser. From there, proceed to the section *Running the Setup*

.. TODO:: redo text: 1) provision vagrant box and run all-in-one installer, here's a sample Vagrant file 2) if you are hacking on stackstorm, we recommend st2workroom, list benefits.


For getting |st2| on Vagrant, refer to :ref:`all_in_one-vagrant` section of :doc:`./all_in_one`.

NOTE: the `st2express/Vagrant <https://github.com/StackStorm/st2express>`__ is deprecated in _v0.13_.
