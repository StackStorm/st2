Configure SSH 
=================================

To run actions on remote hosts, StackStorm uses `Fabric <http://www.fabfile.org/>`_. 

Configure passwordless SSH to run actions on remote hosts.  

StackStorm ssh user and a path to SSH key are set in ``/etc/st2/st2.conf``. During installation, ``st2_deploy.sh`` script configures ssh on the local box for a user ``stanley``. 

.. todo:: (phool, lakshmi?) Describe ssh configurations on the remote boxes. Add "verification" section, with something like 'be sure that `ssh -t hostname uname -a' works.
   
Troubleshooting
-----------------

* Validate that passwordless SSH configuration works fine for the destination:

    .. code-block:: bash

        sudo ssh -i /home/stanley/.ssh/stanley_rsa -t stanley@host.example.com uname -a

.. include:: /engage.rst
