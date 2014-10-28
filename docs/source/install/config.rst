Configuration
==============
.. note:: If you are using "all in one" installation, all configuration is already set up. 

StackStorm configuration file is at :github_st2:`/etc/st2/st2.conf </conf/st2.conf>`

SUDO Access
-------------------------

.. todo:: (Manas) please describe 1) we run st2 as a user, it's in config file, it needs sudo.

Configure SSH 
----------------

To run actions on remote hosts, StackStorm uses `Fabric <http://www.fabfile.org/>`_.

Configure passwordless SSH to run actions on remote hosts.

StackStorm ssh user and a path to SSH key are set in ``/etc/st2/st2.conf``. During installation, ``st2_deploy.sh`` script configures ssh on the local box for a user `stanley`.

.. todo:: (phool, lakshmi?) Describe ssh configurations on the remote boxes. Add "verification" section, with something like 'be sure that `ssh -t hostname uname -a` works'.
 
SSH Troubleshooting
~~~~~~~~~~~~~~~~~~~~

* Validate that passwordless SSH configuration works fine for the destination. Assuming default user `stanley`:

    .. code-block:: bash

        sudo ssh -i /home/stanley/.ssh/stanley_rsa -t stanley@host.example.com uname -a


Configure Logging 
-------------------
By default, the logs are in ``/opt/var/st2``. 

* To configure logging with syslog, grab the configuration and follow instructions at :github_contrib:`st2contrib/extra/syslog </extra/syslog>`

* Check out LogStash configuration and Kibana dashboard for pretty logging and audit at :github_contrib:`st2contrib/extra/logstash </extra/logstash>`


.. include:: /engage.rst
