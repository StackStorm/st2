Puppet Module
=============
|st2| provides a supported Puppet module for use when deploying in an existing Puppet infrastructure. This module is designed to allow relative flexibility with the configuration methods and management techniques of the StackStorm application.

This module aims to provide sane default configurations, but also stay out of your way in the event you need something more custom. To accomplish this, this module uses the Roles/Profiles pattern. Included in this module are several modules that come with sane defaults that you can use directly or use to compose your own site-specific profile for StackStorm installation.

Supported Operating Systems
---------------------------
As of this writing, the following operating systems are supported:

* Ubuntu 14.04 LTS
* RedHat/CentOS 7.x
* Fedora 20

Support under development:
 
* RedHat/CentOS 6.x

Note: A Puppet module for RHEL 6.x exists at https://github.com/StackStorm/puppet-st2-el6. This module is being merged into the mainline module shortly.


Installation
------------
The Puppet module is updated frequently, and uploaded to the Puppet Forge on each release. You can find the module at https://forge.puppetlabs.com/stackstorm/st2

Manual Installation
~~~~~~~~~~~~~~~~~~~
The ``puppet module install`` action will install a module and all of its dependencies. By default, it will install into the first directory in Puppet’s modulepath. To install the module from the Puppet Forge, simply type the following command:

::

   puppet module install stackstorm-st2

Puppetfile
~~~~~~~~~~
Alternatively, you can install this module using ``librarian-puppet`` or ``r10k`` and add this file to your ``Puppetfile``. Add the following line:

::

   mod "stackstorm/st2"

Getting Started
---------------
Getting started is very easy. Several pre-configured profiles have been included out-of-the-box to get you started with minimal effort. We will go over this method, as well as how to consume the individual portions of the module.


Quick Start
~~~~~~~~~~~
For a full installation on a single node, a profile already exists to get you setup and going with minimal effort. Simply add the following class declaration to your site or node manifest.

::

   include ::st2::profile::fullinstall

This module will install StackStorm and all its dependencies with sane defaults. This class is a great way to test out StackStorm in your environment, or to take a look at how each of the different components composes to create a StackStorm installation profile.

Profiles
~~~~~~~~
In addition to providing a full-install profile, each of the separate profiles are broken up to allow flexibly in defining a site-specific StackStorm profile. Within the module exist several default-configured profiles for the components of StackStorm and its dependencies.

The full list of profiles are:

* ``st2::profile::client``      - Profile to install all client libraries for st2
* ``st2::profile::fullinstall`` - Full installation of StackStorm and dependencies
* ``st2::profile::mistral``     - Install of OpenStack Mistral
* ``st2::profile::mongodb``     - st2 configured MongoDB installation
* ``st2::profile::nodejs``      - st2 configured NodeJS installation
* ``st2::profile::python``      - Python installed and configured for st2
* ``st2::profile::rabbitmq``    - st2 configured RabbitMQ installation
* ``st2::proflle::server``      - st2 server components
* ``st2::profile::web``         - st2 web components

When composing a site-profile, select the various components of the StackStorm installation to deploy. An example configuration profile can be found in the *st2workroom* project at http://git.io/v3Z5B.

Configuration
-------------
Configuration can be done directly via code composition, or set via Hiera data bindings. By design, all of the configuration options available to the user are set at the top-level of the module. The configuration values are:

*  ``version``            - Version of StackStorm to install
*  ``revision``           - Revision of StackStorm to install
*  ``mistral_git_branch`` - Tagged branch of Mistral to download/install
*  ``api_url``            - URL where the StackStorm API lives (default: undef)
*  ``auth``               - Toggle to enable/disable auth (Default: false)
*  ``auth_url``           - URL where the StackStorm WebUI lives (default: undef)
*  ``cli_base_url``       - CLI config - Base URL lives
*  ``cli_api_version``    - CLI config - API Version
*  ``cli_debug``          - CLI config - Enable/Disable Debug
*  ``cli_cache_token``    - CLI config - True to cache auth token until expries
*  ``cli_username``       - CLI config - Auth Username
*  ``cli_password``       - CLI config - Auth Password
*  ``cli_api_url``        - CLI config - API URL
*  ``cli_auth_url``       - CLI config - Auth URL
*  ``workers``            - Set the number of actionrunner processes to start
*  ``ng_init``            - [Experimental] Init scripts for services. Upstart ONLY

Class Configuration
~~~~~~~~~~~~~~~~~~~
Any of the module configuration settings can be set at declaration. An example of this:

::

   class { '::st2':
     auth     => true,
     auth_url => 'https://st2auth.stackstorm.net',
   }

When composing your own profile, you can include `Class[::st2]` into your catalog to set any variables necessary.

Hiera Configuration
~~~~~~~~~~~~~~~~~~~
Likewise, module configuration can be set via Hiera. For example in a hiera data file:

::

   st2::auth: true
   st2::auth_url: https://st2auth.stackstorm.net

Pack Installation and Management
--------------------------------

StackStorm packs can be installed and configured directly from Puppet. This can be done via the `st2::pack` and `st2::pack::config` defined types.

Defined Types
~~~~~~~~~~~~~

::

    st2::pack { 'linux': }
    st2::pack { ['librato', 'consul']:
      repo_url => 'https://github.com/StackStorm/st2incubator.git',
    }
    st2::pack { 'slack':
      repo_url => 'https://github.com/StackStorm/st2incubator.git',
      config     => {
        'post_message_action' => {
          'webhook_url'         => 'XXX',
        },
      },
    }

Hiera
~~~~~
In order to load packs via hiera, you will need to include the `::st2::packs` class in your site profile. Then, values will be read from Hiera.

::

    st2::packs:
    linux:
        ensure: present
    cicd:
        ensure: present
        repo_url: https://github.com/StackStorm/st2incubator.git
    slack:
        ensure: present
        repo_url: https://github.com/StackStorm/st2incubator.git
        config:
        post_message_action:
            webhook_url: XXX
