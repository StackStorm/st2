All-in-one Installer
====================
|st2| provides an all-in-one installer aimed at assisting users with the initial setup and configuration. The installer comes pre-bundled in a number of different provisioning options for convenience, or can also be manually deployed and installed manually on a server.

.. warning:: This new and shiny all-in-one installer is soon going to become default. It provides production-level functionality, graphical setup, and based on more reliable architecture. But warn you, it is in BETA. Please give it a try, report bugs and ask for improvements. If you prefer stability, use st2_deploy from the :doc:`/install/index` doc.

While in beta, OS support will start at our most commonly used platforms and be added before final release. At present, supported platforms are:

* Ubuntu 14.04

Certification is currently planned and/or underway for:

* Debian 7/8
* CentOS / RHEL 6.x and 7.x
* Ubuntu LTS 12.04

If your platform is not listed here and you would like it to be, please drop us a line at `support@stackstorm.com <email:support@stackstorm.com>` and let us know.

Pre-Requisites
--------------
Before getting started, it is necessary to do a bit of pre-planning to integrate |st2| into an environment. Below is a checklist of items to prepare before running the installer.

#. A server. See below for the list of pre-bundled options - including a VMDK for VMware environments and an AMI image which can be great for trying us out on AWS, or bring your own.
#. Hostname of new server setup with DNS.
#. Admin Password.
#. Administrative SSH Public/Private Keys *(Optional)*
#. SSL Certificates *(Optional)*
#. Chat service connection credentials *(Optional)*

The initial setup is designed to configure itself to a freshly deployed server with no additional services running. If you do not have or do not wish to provide SSL and SSH keys during the initial setup, |st2| will generate random new keys automatically.

Sizing the Server
~~~~~~~~~~~~~~~~~
A standard all-in-one installation has all of the various components of |st2|, as well as the supporting infrastructure components. While the system can operate with less equipped servers, these are recommended for the best experience while testing or deploying |st2|.

Testing
+++++++
* Single or Dual CPU system
* At least 2GB of RAM
* Recommended EC2: **m3.medium**

Production
++++++++++
* Quad core CPU system
* >16GB RAM
* Recommended EC2: **m4.xlarge**

Deployment Options
-------------------------

Bring Your Own Box
~~~~~~~~~~~~~~~~~~
|st2| provides a bash-based bootstrap script that is used to bootstrap a computer with StackStorm. It is highly recommended to run this script on a clean base OS. To get started, run the following command.

::

    curl -sSL https://raw.githubusercontent.com/StackStorm/st2workroom/master/script/bootstrap-st2express | sudo bash

You will need elevated privileges in order to run this script. This will boot up a fresh |st2| installation along with the Mistral workflow engine on Ubuntu 14.04 LTS. While loading, some console output in red is expected and can be safely ignored. Once completed, you will see the following console output.

.. include:: /_includes/install/ok.rst

Visit the setup URL output on your command line by entering the address in your web browser. From there, proceed to the section *Running the Setup*

Amazon Web Services (AWS)
~~~~~~~~~~~~~~~~~~~~~~~~~
|st2| provides pre-built AMI images containing the latest stable release of |st2|. These images come equipped with the *All-in-one installer* to help you get setup quickly and easily. To get started:

#. From the AWS Marketplace, select |st2|
#. Select the instance type/size. For assistance in choosing an instance type, refer to the *Sizing the Server* section above. Click **Next: Configure instance details**.
#. Set any configuration details. Click **Next: Add Storage**
#. Set up any applicable tags for your instance. Click **Next: Configure Security Group**
#. Setup a security group. It is recommended that you leave the default settings. Port 443 must be available for the WebUI, port 9100 for |st2| authentication, and port 9101 for the |st2| API
#. Review your settings, and then click Launch.
#. In the **Select an existing key pair or create a new key pair** dialog box, select **Choose an existing key pair** to select a new key pair that you already created or create a new key pair. Select the acknowledgment check box, and then click **Launch Instances**. This can take approximately 5-15 minutes to launch. A confirmation page will appear, letting you know that your instance is launching. Click **View Instances** to close the confirmation and return to the AWS Console.
#. From **Instances**, make note of the **Instance ID**, **Public IP** and **Public DNS**
#. In your web browser, enter the |st2| setup URL. The format will be: https://**Public IP**/setup
#. Enter the username and password to log in. The username is *installer*, and the password is your **Instance ID**
#. Proceed to the section *Running the installer*

 .. _all_in_one-vagrant:

Vagrant
~~~~~~~
|st2| provides pre-built Vagrant boxes for both `VirtualBox <https://www.virtualbox.org>` and `VMWare <https://www.vmware.com>` providers. By default, the setup will install the lastest stable release of |st2|.

::

   git clone https://github.com/StackStorm/st2workroom.git st2workroom
   cd st2workroom
   vagrant up st2express


If you have previously used deployed |st2| and downloaded the st2express box it might be a good idea to update the box. If this is your absolute first install of |st2| then skip this step.

::

  vagrant box update st2express


This will boot up a fresh |st2| installation along with the Mistral workflow engine on Ubuntu 14.04 LTS. While loading, some console output in red is expected and can be safely ignored. Once completed, you will see the following console output.

.. include:: /_includes/install/ok.rst

Visit the setup URL output on your command line by entering the address in your web browser. From there, proceed to the section *Running the Setup*

.. _all_in_one-running_the_setup:

Running the Setup
~~~~~~~~~~~~~~~~~
Once the machine is provisioned, you will need to configure |st2| to integrate with your environment. Before you see the initial setup screen, you may be presented with a SSL certificate warning. A brand new self-signed SSL certificate was created, and you will need to trust this certificate to continue.

Step 1: Configuring Hostname and SSL
++++++++++++++++++++++++++++++++++++

.. figure:: /_static/images/st2installer_step_1.png

In this step, you will be setting up the networking for |st2|. Here, you will configure the hostname of the new server and optionally upload SSL certificates to be used by the StackStorm WebUI, Auth, and API HTTP endpoints.

#. Enter the FQDN of the |st2| server. This FQDN should be setup in your DNS server
#. *(Optional)* Choose to send anonymous data to StackStorm.
#. Select either **Continue with self-signed** to continue with the automatically generated SSL certificates, or **Upload SSL Certificate** to upload public/private SSL keys.
#. Click **Next**

Note: Uploaded SSL certificates should be in X509 ASCII/Base64 armored format.

Step 2: Setup user accounts
+++++++++++++++++++++++++++

.. figure:: /_static/images/st2installer_step_2.png


In this step, you will be setting up the Administrator account for you, and the administrative account for StackStorm. In the upper section, you will be asked to enter a new password. This password will be used with the account **admin**, created on the box with `sudo` privileges. In the lower section, you will setup the account that StackStorm will use to log into remote servers via SSH, and execute commands. Make note of the generated SSH key pair if you choose that option, and distribute this key to your servers.

#. Enter a new password, containing at least 8 characters, with at least one digit and at least one letter.
#. Confirm the new password in the box below.
#. Enter or confirm the name of the server admin account. This account will be used to SSH into remote servers
#. Select either **Generate a new SSH key pair for the account** or **Use an existing key pair**.
#. Click **Next**

Note: Uploaded SSH keys should be *RSA* in type, and the public key should omit the key-type and server comment fields. For example:

::

   ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwPYLqtmPSs/xjpTtuI71SJSSvZYa0qIRi9Rgd+eiWm4VT43F8/vwAuc+3VpaaNnu+f5emXasbk/hHP+lH/fCjWzS+yrUvJluIuzOfIuAmKpV9rYSgDiRwCgp1fpU2C4QtJW9KUVQdmvIrW+gi8Z66kZ2307oNHlyDv5jBv4wO9dYirSRvg+32YW03BEe2as47Ux5r1I0MvjsVQoTsLRZNjPdUjTwkgPY8k2YE+AMI22EonqiU4XZPUouGP3qFZqKgKjVYfVfaZ7B+ezBDkn4sFJeiOTqalsWrqlL6UWbVSExN8ZUaJr0ZO5WNmB9tUU6xb8K8LvINtqnPOR14NWVZ james@stackstorm.com

simply becomes...

::

   AAAAB3NzaC1yc2EAAAADAQABAAABAQCwPYLqtmPSs/xjpTtuI71SJSSvZYa0qIRi9Rgd+eiWm4VT43F8/vwAuc+3VpaaNnu+f5emXasbk/hHP+lH/fCjWzS+yrUvJluIuzOfIuAmKpV9rYSgDiRwCgp1fpU2C4QtJW9KUVQdmvIrW+gi8Z66kZ2307oNHlyDv5jBv4wO9dYirSRvg+32YW03BEe2as47Ux5r1I0MvjsVQoTsLRZNjPdUjTwkgPY8k2YE+AMI22EonqiU4XZPUouGP3qFZqKgKjVYfVfaZ7B+ezBDkn4sFJeiOTqalsWrqlL6UWbVSExN8ZUaJr0ZO5WNmB9tUU6xb8K8LvINtqnPOR14NWVZ

Step 3: Configure ChatOps
+++++++++++++++++++++++++

.. figure:: /_static/images/st2installer_step_3.png


In this step, you will setup ChatOps. ChatOps is a core feature of StackStorm, allowing you to collaborate and work more effectively by executing actions inside of a chat room. This step will setup Hubot and pre-configure it to connect to StackStorm as well as to your selected Chat service. While this is an optional feature and can be in the event that you have your own Hubot installation, or do not want to install this feature, we highly recommend experimenting with the feature in your daily operational workflows.

#. If you have your own Hubot installation already, click on **configure your existing Hubot instance**.
#. Select the Chat Service that you wish to connect to
#. Enter the appropriate configuration information for a bot user account on your chat service
#. Click **Get Started**
