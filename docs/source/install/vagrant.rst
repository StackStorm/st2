Vagrant
=======

Here is how to get |st2| up and running with Vagrant.

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
* `puppetlabs/centos-7.0-64-nocm`
* `puppetlabs/ubuntu-14.04-64-nocm`

It is very possible that other baseboxes with the same OS will work just fine. However, if you run into issues, these are boxes that should get you going without fuss. These are the same boxes that are used in the `st2workroom` project mentioned in the Quick Start Above.

We are constantly striving to ensure that we have compatability with as many platforms as we can. However, if you find a basebox that doesn't work, please let us know and we'll be glad to take a look. We also love Pull Requests from the community, and might have some goodies if you help us out!

Sample Vagrantfile
~~~~~~~~~~~~~~~~~~

Below is an an example of a Vagrantfile capable of loading StackStorm. This minimal Vagrantfile will load up a machine and provision a clean StackStorm installation.This configuration also includes a `public_network` setting, which is necessary to allow your host environment to access the StackStorm guest machine. If you choose not to use this configuration, make sure that you have an interface configured that you can access via the Host Machine.

::

    Vagrant.configure(2) do |config|
      config.vm.network "public_network"
      config.vm.box = "puppetlabs/ubuntu-14.04-64-nocm"
      config.vm.provider "virtualbox" do |v|
        v.memory = 1024
      end
      config.vm.provision "shell",
          inline: "curl -sSL https://install.stackstorm.com/ | sudo su"
    end
