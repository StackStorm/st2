Vagrant
=======

|st2| provides pre-built Vagrant boxes for both `VirtualBox <https://www.virtualbox.org>`_ and `VMWare <https://www.vmware.com>`_ providers. By default, the setup will install the lastest stable release of |st2|. These boxes are hosted on the `Hashicorp Atlas <https://atlas.hashicorp.com/stackstorm/boxes/st2>`_ website.

Using these vagrant images, it is possible to setup:

* Spin up a test environment to play with StackStorm (`st2`)
* Spin up a development environment to work with StackStorm (`st2dev`)
* Begin building infrastructure patterns using pre-configured Config Management tools

You can also create your own Vagrant VM and run :doc:<all_in_one>.

NOTE: the `st2express/Vagrant <https://github.com/StackStorm/st2express>`__ is deprecated in _v0.13_.

Quick Start with st2workroom
----------------------------

If you are new to Vagrant, or to StackStorm, we have made a repository all setup with the necessary configuration to run a Vagrant box. This includes pre-configured virtual machine settings out of the box. This is a great way to get started quickly and easily.

::

   git clone https://github.com/StackStorm/st2workroom.git st2workroom
   cd st2workroom
   vagrant up st2


If you have previously used deployed |st2| and downloaded the st2express box it might be a good idea to update the box. If this is your absolute first install of |st2| then skip this step.

::

  vagrant box update st2


This will boot up a fresh |st2| installation along with the Mistral workflow engine on Ubuntu 14.04 LTS. While loading, some console output in red is expected and can be safely ignored. Once completed, you will see the following console output.

.. include:: /_includes/install/ok.rst

Once installed, you have the option of logging into the virtual machine with this command:

::

    vagrant ssh st2

Likewise, you have the option to run the All-in-one GUI setup. Using this tool, you can quickly configure your StackStorm system including user accounts, ChatOps support, and enable Enterprise Features. Refer to :ref:`all_in_one-running_the_setup` section of :doc:`./all_in_one` for more information.


Run Vagrant with All-In-One Installer
-------------------------------------
Requirements
~~~~~~~~~~~~

In order to successfully deploy StackStorm to a Vagrant environment, you must ensure the following conditions are satisified. Namely:

* VM has >1GB RAM (2GB RAM recommended)
* VM has a NIC interface the user can access from the host machine

Once setup, the next step is to run the StackStorm installer. This will pull down and setup all the necessary items to run StackStorm Using this tool, you can quickly configure your StackStorm system including user accounts, ChatOps support, and enable Enterprise Features. Refer to :ref:`all_in_one-running_the_setup` section of :doc:`./all_in_one` for more information.

Supported Baseboxes
~~~~~~~~~~~~~~~~~~~

We have currently done testing and certified that StackStorm Installer works properly on the following Vagrant Baseboxes:

* `puppetlabs/centos-6.6-64-nocm`
* `puppetlabs/centos-7-0-64-nocm`
* `puppetlabs/ubuntu-14.04-64-nocm`

It is very possible that other baseboxes with the same OS will work just fine. However, if you run into issues, these are boxes that should get you going without fuss. These are the same boxes that are used in the `st2workroom` project mentioned in the Quick Start Above.

We are constantly striving to ensure that we have compatability with as many platforms as we can. However, if you find a basebox that doesn't work, please let us know and we'll be glad to take a look. We also love Pull Requests from the community, and might have some goodies if you help us out!

Sample Vagrantfile
~~~~~~~~~~~~~~~~~~

Below is an an example of a Vagrantfile capable of loading StackStorm. This Vagrantfile will load up a machine and provision a clean StackStorm installation. This configuration also includes a `public_network` setting, which is necessary to allow your host environment to access the StackStorm guest machine. If you choose not to use this configuration, make sure that you have an interface configured that you can access via the Host Machine.

.. literalinclude:: ../../../scripts/Vagrantfile
   :language: ruby


