Vagrant
=======

|st2| provides pre-built Vagrant boxes for both `VirtualBox <https://www.virtualbox.org>` and `VMWare <https://www.vmware.com>` providers. By default, the setup will install the lastest stable release of |st2|. These boxes are hosted on the `Hashicorp Atlas <https://atlas.hashicorp.com/stackstorm/boxes/st2>` website.

Using these vagrant images, it is possible to setup:

* Spin up a test environment to play with StackStorm (`st2`)
* Spin up a development environment to work with StackStorm (`st2dev`)
* Begin building infrastructure patterns using pre-configured Config Management tools

Quick Start
-----------

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

NOTE: the `st2express/Vagrant <https://github.com/StackStorm/st2express>`__ is deprecated in _v0.13_.

Requirements
------------

In order to successfully deploy StackStorm to a Vagrant environment, you must ensure the following conditions are satisified. Namely:

* VM has >1GB RAM (2GB RAM recommended)
* VM has a NIC interface the user can access from the host machine

Once setup, the next step is to run the StackStorm installer. This will pull down and setup all the necessary items to run StackStorm Using this tool, you can quickly configure your StackStorm system including user accounts, ChatOps support, and enable Enterprise Features. Refer to :ref:`all_in_one-running_the_setup` section of :doc:`./all_in_one` for more information.

Below is an aexample of a Vagrantfile capable of loading StackStorm. This minimal Vagrantfile will load up a machine and provision a clean StackStorm installation

::

    Vagrant.configure(2) do |config|
      config.vm.network "public_network"
      config.vm.box = "puppetlabs/ubuntu-14.04-64-nocm"
      config.vm.provider "virtualbox" do |v|
        v.memory = 1024
      end
      config.vm.provision "shell",
          inline: "curl -sSL http://stackstorm.com/install.sh | sudo su"
    end
