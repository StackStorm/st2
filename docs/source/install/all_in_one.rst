All-in-one Installer
********************
|st2| provides an all-in-one installer aimed at assisting users with the initial setup and configuration. The installer comes pre-bundled in a number of different provisioning options for convenience, or can also be manually deployed and installed manually on a server.

That's OK! You're busy, we get it. How do you just get started? Get your own box, and run this command:

::

   curl -sSL https://install.stackstorm.com/ | sudo sh


.. contents:: Want to learn more? Read on! We will make it worth your while.

What is it?
###########

The All-in-one installer is an opinionated installation of |st2| that allows you to get up and going on a single instance very quickly. Using this method, we download and configure |st2| using our best practices for deployment. This makes the All-in-one installer good to use when starting out with |st2| in Proof-of-concepts or initial production deployments. It also serves as a good baseline for review how all the various components interact as you build out larger, scaled |st2| deployments.

The All-in-one installer is comprised of three |st2| projects. They are:

* `puppet-st2 <https://github.com/stackstorm/puppet-st2>`_. This is our supported Puppet module used to install and setup |st2|.
* `st2workroom <https://github.com/stackstorm/st2workroom>`_ is scaffolding built around Puppet. It allows you to spin up Vagrant images or deploy on a bare-metal server in much the same way
* `st2installer <https://github.com/stackstorm/st2installer>`_. This is the GUI installer that is used to configure |st2|, the initial admin user to access the CLI and WebUI, and ChatOps. This application generates an answer file that is then passed to `st2workroom` to bootstrap your installation.

Using these three projects, it is possible to get |st2| setup with the following components:

* |st2| Core - Stable or Latest version
* OpenStack Mistral Workflow Engine
* Hubot ChatOps Robot
* MongoDB (supporting infrastructure)
* RabbitMQ (supporting infrastructure)
* PostgreSQL (supporting infrastructure)
* nginx (SSL termination, WSGI, serving static content)

Optionally, you can also provide an Enterprise License Key and get access to the following features:

* |st2| FLOW - HTML5 based Graphical Workflow editor. Use this to visualize, edit, and share workflows.
* |st2| Role Based Access Control. Apply fine-grained controls to actions and rules to fit into the most complex of environments.
* |st2| LDAP Authentication Support. Integrate with your existing authentication directory.G

Supported Platforms
###################

At present, supported platforms are:

* Ubuntu 14.04
* CentOS / RHEL 6.x and 7.x

Certification is currently planned and/or underway for:

* Debian 7/8

If your platform is not listed here and you would like it to be, please drop us a line at `support@stackstorm.com <email:support@stackstorm.com>`_ and let us know.

Pre-Requisites
##############

Before getting started, it is necessary to do a bit of pre-planning to integrate |st2| into an environment. Below is a checklist of items to prepare before running the installer.

#. A server. See below for the list of pre-bundled options - including a VMDK for VMware environments and an AMI image which can be great for trying us out on AWS, or bring your own.
#. Hostname and IP of new server. IP must be externally addressible from the target install box.
#. Admin Password.
#. Administrative SSH Public/Private Keys *(Optional)*
#. SSL Certificates *(Optional)*
#. Chat service connection credentials *(Optional)*

The initial setup is designed to configure itself to a freshly deployed server with no additional services running. If you do not have or do not wish to provide SSL and SSH keys during the initial setup, |st2| will generate random new keys automatically.

.. rubric:: Sizing the Server

A standard all-in-one installation has all of the various components of |st2|, as well as the supporting infrastructure components. While the system can operate with less equipped servers, these are recommended for the best experience while testing or deploying |st2|.

+--------------------------------------+-----------------------------------+
|            Testing                   |         Production                |
+======================================+===================================+
|  * Single or Dual CPU system         | * Quad core CPU system            |
|  * At least 2GB of RAM               | * >16GB RAM                       |
|  * Recommended EC2: **m3.medium**    | * Recommended EC2: **m4.xlarge**  |
+--------------------------------------+-----------------------------------+


Deployment Options
##################

Bring Your Own Box
==================

|st2| provides a bash-based bootstrap script that is used to bootstrap a computer with |st2|. It is highly recommended to run this script on a clean base OS. To get started, run the following command.

::

   curl -sSL https://install.stackstorm.com/ | sudo sh

You will need elevated privileges in order to run this script. This will boot up a fresh |st2| installation along with the Mistral workflow engine on Ubuntu 14.04 LTS. While loading, some console output in red is expected and can be safely ignored. Once completed, you will see the following console output.

.. include:: /_includes/install/ok.rst

Visit the setup URL output on your command line by entering the address in your web browser. From there, proceed to the section *Running the Setup*

Amazon Web Services (AWS)
=========================

We have currently performed testing and certified that StackStorm Installer works properly on the following AMI Images:

* CentOS 6     - `ami-1255b321`
* CentOS 7     - `ami-d440a6e7`
* Ubuntu 14.04 - `ami-5189a661`

It is highly likely that the installer will also work on different AMIs if it is one of our Supported Operating Systems. However, if you run into issues, these are AMIs that we use in our automated testing and should get you going with minimal fuss.

We are constantly striving to ensure that we have compatability with as many platforms as we can. However, if you find an AMI that doesn't work, please let us know and we'll be glad to take a look. We also love Pull Requests from the community, and might have some goodies if you help us out!


Getting started with AWS is easy! Follow the instructions below to provision a server with the appropriate security settings, and then run the All-in-one installer script.

#. From the AMI Community Marketplace, select the appropriate AMI image. Suggestions are recommended above.
#. Select the instance type/size. For assistance in choosing an instance type, refer to the *Sizing the Server* section above. Click **Next: Configure instance details**.
#. Set any configuration details. Click **Next: Add Storage**
#. Set up any applicable tags for your instance. Click **Next: Configure Security Group**
#. Setup a security group. It is recommended that you leave the default settings. Port 443 must be available for the WebUI, port 9100 for |st2| authentication, and port 9101 for the |st2| API
#. Review your settings, and then click Launch.
#. In the **Select an existing key pair or create a new key pair** dialog box, select **Choose an existing key pair** to select a new key pair that you already created or create a new key pair. Select the acknowledgment check box, and then click **Launch Instances**. This can take approximately 5-15 minutes to launch. A confirmation page will appear, letting you know that your instance is launching. Click **View Instances** to close the confirmation and return to the AWS Console.
#. In your web browser, enter the |st2| setup URL. The format will be: https://**Public IP**/setup
#. Run the BYOB installer command above.
#. Once finished, Proceed to the section *Running the installer*

.. _all_in_one-running_the_setup:

Running the Setup
#################
Once the machine is provisioned, you will need to configure |st2| to integrate with your environment. Before you see the initial setup screen, you may be presented with a SSL certificate warning. A brand new self-signed SSL certificate was created, and you will need to trust this certificate to continue.

Step 1: Configuring Hostname and SSL
====================================

.. figure:: /_static/images/st2installer_step_1.png

In this step, you will be setting up the networking for |st2|. Here, you will configure the hostname of the new server and optionally upload SSL certificates to be used by the |st2| WebUI, Auth, and API HTTP endpoints. You will also specify your StackStorm Enterprise license key if you have one.

#. Enter the FQDN of the |st2| server. This FQDN should be setup in your DNS server
#. *(Optional)* Choose to send anonymous data to |st2|.
#. Select either **Continue with self-signed** to continue with the automatically generated SSL certificates, or **Upload SSL Certificate** to upload public/private SSL keys.
#. *(Optional)* Enable the Enterprise features. If you don't have a license key, request a 30-day trial at `stackstorm.com <https://stackstorm.com/product#enterprise>`_.
#. Click **Next**

Note: Uploaded SSL certificates should be in X509 ASCII/Base64 armored format.

Step 2: Setup user accounts
===========================

.. figure:: /_static/images/st2installer_step_2.png


In this step, you will be setting up the Administrator account for you, and the administrative account for |st2|. In the upper section, you will be asked to enter a new password. This password will be used with the account **admin**, created on the box with `sudo` privileges. In the lower section, you will setup the account that |st2| will use to log into remote servers via SSH, and execute commands. Make note of the generated SSH key pair if you choose that option, and distribute this key to your servers.

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
=========================

.. figure:: /_static/images/st2installer_step_3.png


In this step, you will setup ChatOps. ChatOps is a core feature of |st2|, allowing you to collaborate and work more effectively by executing actions inside of a chat room. This step will setup Hubot and pre-configure it to connect to |st2| as well as to your selected Chat service. While this is an optional feature and can be in the event that you have your own Hubot installation, or do not want to install this feature, we highly recommend experimenting with the feature in your daily operational workflows.

#. If you have your own Hubot installation already, click on **configure your existing Hubot instance**.
#. Select the Chat Service that you wish to connect to
#. Enter the appropriate configuration information for a bot user account on your chat service
#. Click **Get Started**

Changing Configuration
######################

At any point after installation, it is possible to update the StackStorm configuration to reconfigure basic settings, SSL setup, ChatOps configuration. You can even upgrade a StackStorm community install to an Enterprise install very easily.

To update or change settings, you will create a configuration file at :code:`/opt/puppet/hieradata/answers.yaml`, and then run the :code:`update-system` command. The installer will then run and reconfigure your system appropriately.

Make sure to protect this file, and make it only readable by the ``root`` user. This file could contain secrets.

.. rubric:: Configurable Settings


Below includes a list of settings that can be supplied to the All-in-one installer.


System Configuration Values
===========================

These settings are used to inform NGINX setup, SSL setup, and any network proxy information.

* :code:`system::hostname`    - Hostname of the server (used for SSL generation)
* :code:`system::fqdn`        - Fully Qualified Domain Name for the server
* :code:`system::ipaddress`   - IP address of the external IP to access |st2|. This IP address *must* be reachable from outside this box.
* :code:`system::http_proxy`  - HTTP proxy server
* :code:`system::https_proxy` - HTTPS proxy server

|st2| Configuration Values
==========================

* :code:`st2::version`                  - Version of |st2| to deploy (default: latest stable)
* :code:`st2::revision`                 - Revision of |st2| to deploy (default: latest stable)
* :code:`st2::api_url`                  - |st2| API URL (if not on the same machine)
* :code:`st2::auth_url`                 - |st2| Auth URL (if not on the same machine)
* :code:`st2::ssl_public_key`           - SSL Public key used with HTTPS auth. Must provide the actual key contents
* :code:`st2::ssl_private_key`          - SSL Private key used with HTTPS auth. Must provide the actual key contents
* :code:`st2::stanley::username`        - Username for default remote SSH user
* :code:`st2::stanley::ssh_public_key`  - SSH Public Key for default remote SSH user. Must provide the actual key contents.
* :code:`st2::stanley::ssh_private_key` - SSH Private Key for default remote SSH user. Must provide the actual key contents.


|st2| Enterprise Configuration Values
=====================================

* :code:`st2enterprise::token` - This is the Enterprise Auth Token provided by |st2| to enable the enterprise features. Visit `stackstorm.com <https://stackstorm.com/product#enterprise>`_ for more details.
* :code:`st2::ldap::host`      - LDAP host to connect to (e.g.: ldap.stackstorm.net)
* :code:`st2::ldap::port`      - LDAP port to connect to (default: 389)
* :code:`st2::ldap::use_ssl`   - LDAP Enable SSL (default: false)
* :code:`st2::ldap::use_tls`   - LDAP Enable TLS (default: false)
* :code:`st2::ldap::base_dn`   - LDAP Base DN (e.g: ou=Users,dc=stackstorm,dc=net)
* :code:`st2::ldap::id_attr`   - LDAP attribute search (default: uid)
* :code:`st2::ldap::scope`     - LDAP Search Scope (default: subtree)


Hubot Configuration Values
==========================

These values directly correspond to configure the Hubot adapter, Hubot environment variables, and required NPM libraries to get started. We have done our best to include several example configurations that you can [find in our |st2| workroom](https://github.com/StackStorm/st2workroom/blob/master/hieradata/workroom.yaml.example)

If for whatever reason your chat client is not listed as an example, it is possible to add *any* Hubot chat service via this method. Refer to the plugin details for more information. In general, you'll need to understand the NPM dependencies, and any environment variables that need to be set.

Below are the values you can set

* :code:`hubot::chat_alias`        - A short for a command used at the beginning of task. (e.g.: !)
* :code:`hubot::adapter`           - The name of the npm adapter used to connect to your chat service
* :code:`hubot::env_export`        - A hash of all environment variables necessary to configure the :code:`hubot::adapter`
* :code:`hubot::external_scripts`  - An array of all external hubot scripts to load on startup
* :code:`hubot::dependencies`      - a hash of all npm dependencies needed your your chat adapter.


Example Answers File
====================

::

   ---
    ### Hipchat Example Config
    ## See https://github.com/hipchat/hubot-hipchat#adapter-configuration for more details
    st2enterprise::token: myawesometokentogetenterprisefeatures
    st2::version: 1.0.0
    st2::revision: 1
    hubot::chat_alias: "!"
    hubot::adapter: "hipchat"
    hubot::env_export:
     HUBOT_LOG_LEVEL: "debug"
     HUBOT_HIPCHAT_JID: "XXX"
     HUBOT_HIPCHAT_PASSWORD: "XXX"
     HUBOT_XMPP_DOMAIN: "XXX" # Use only if using HipChat Server Beta
     ST2_CHANNEL: "hubot"
     ST2_AUTH_USERNAME: "testu"
     ST2_AUTH_PASSWORD: "testu"
     EXPRESS_PORT: 8081
    hubot::external_scripts:
      - "hubot-stackstorm"
    hubot::dependencies:
      "hubot": ">= 2.6.0 < 3.0.0"
      "hubot-scripts": ">= 2.5.0 < 3.0.0"
      "hubot-hipchat": ">=2.12.0 < 3.0.0"
      "hubot-stackstorm": ">= 0.1.0 < 0.2.0"

Updating
########

Once you've installed with the All-in-one installer, you will download the latest stable release. If you would like to upgrade to newer versions of StackStorm via the Installer, or follow a specific testing branch, you can do so with the following command:

::

   ENV=<new version> update-system


Each stable release is tagged with a Git Tag, and you can provide that tag at runtime. You can track the unstable branch (`master`) with the following command. Be warned, we attempt to keep this profile passing CI, but it may be unstable.

::

   ENV=master update-system


Unattended Installation
#######################

In addition to the GUI installation method, the All-in-one installer also provides the ability to provide an answers file to pre-seed the installation with values.

The answers file is formatted in standard YAML. Below, we will discuss the various settings you can set in the answers file. Once you have this file, you can kick off the bootstrap with the following command:

::

   curl -sSL https://install.stackstorm.com/ | sudo sh "-a <answers_file>.yaml"


If you have already installed using this method, you can find and update your answers file at `/opt/puppet/hieradata/answers.yaml`


Known Issues
############

We currently do our best to detect the environment that you are in to provide a seemless experience. However, sometimes you may run into a case where we haven't found or explored yet. If you find this, please let us know. Even better, we love when our community submits Pull Requests!


Does not install on RHEL AWS Images
===================================

During installation, you may receive an error about ``ruby-devel`` packages missing, or an inability to compile JSON. Currently, in order to bootstrap a RHEL box, you must ensure you have an active RedHat Satellite account to receive updates. A fix to remove development dependencies is underway.

500 Errors on Connection
========================

When either attempting to connect to the WebUI or CLI, you may see ``500 Internal Error`` alerts. This has to do with the installer not automatically detecting the correct interfaces for StackStorm. While we work on a permanent fix, you can quickly get up and going by doing the following.

* On your system, run ``ifconfig`` and pick a network interface that is externally excessible. Make note of the interface name. (e.g.: ``eth0``)
* Open or create the file ``/opt/puppet/hieradata/answers.yaml``, and add a new line to tell the installer what interface to use.

::

    # For example, if eth0 was an exterally excessible network adapter
    ---
    system::ipaddress: ‘%{::ipaddress_eth0}’`


Installation fails! Oh No!
==========================

As much as it pains us to say, sometimes the installation fails. Right now, the most likely cause for this is an upstream provider having a poor time at the moment of your install. We are actively working to reduce the upstream failure potiential. Best thing to do if something comes up is to simply run ``update-system``

Nginx fails to start w/ Self-signed SSL
=========================================

Maybe you're seeing this error:

::

    nginx[XXX]: nginx: [emerg] SSL_CTX_use_PrivateKey_file("/etc/ssl/st2/st2.key") failed (SSL: error:0B080074:x509 certificate routines:X509_check_private_key:key values mismatch)


In some cases, we have seen the automatic SSL generation create a mis-match between the self-signed certificates. We have only seen this in a few rare cases, and are working to see if we can reliaby reproduce and restore the problem. To fix this problem, simply perform the following steps:

::

    rm -rf /etc/ssl/st2/*
    update-system


This should automatically generate new self-signed SSL certificates, and allow nginx to start
