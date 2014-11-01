Configuration
==============
.. note:: If you are using the "all in one" :doc:`/install/index`, all configurations are already setup.

|st2| configuration file is at :github_st2:`/etc/st2/st2.conf </conf/st2.conf>`

SUDO Access
-------------------------

All actions run by |st2| are performed by a single user. Typically, this user is named ``stanley`` and that is configurable via :github_st2:`st2.conf </conf/st2.conf>`.

.. note:: `stanley` user requires the following access -

    * Sudo access to all boxes on which action will run.
    * As some actions require sudo privileges password-less sudo access to all boxes.

One option of setting up passwordless sudo is perform the below operation on each remote box.

.. code-block:: bash

    echo "stanley    ALL=(ALL)       NOPASSWD: ALL" >> /etc/sudoers.d/st2

.. _config-configure-ssh:

Configure SSH
----------------

To run actions on remote hosts, |st2| uses `Fabric <http://www.fabfile.org/>`_. It is required to configure identity file based SSH access on all remote hosts.

|st2| ssh user and a path to SSH key are set in ``/etc/st2/st2.conf``. During installation, ``st2_deploy.sh`` script configures ssh on the local box for a user `stanley`.

Follow these steps on a remote box to setup `stanley` user on remote boxes.

.. code-block:: bash

    useradd stanley
    mkdir -p /home/stanley/.ssh
    chmod 0700 /home/stanley/.ssh
    # generate ssh keys on |st2| box and copy over public key into remote box.
    # ssh-keygen -f /home/stanley/.ssh/stanley_rsa -P ""
    cp ${KEY_LOCATION}/stanley_rsa.pub /home/stanley/.ssh/stanley_rsa.pub
    # authorize key-base acces.
    cat /home/stanley/.ssh/stanley_rsa.pub >> /home/stanley/.ssh/authorized_keys
    chmod 0600 /home/stanley/.ssh/authorized_keys
    chown -R stanley:stanley /home/stanley
    echo "stanley    ALL=(ALL)       NOPASSWD: ALL" >> /etc/sudoers.d/st2

To verify do the following from the |st2| box

.. code-block:: bash

    # ssh should not require a password since the key is already provided
    ssh -i /home/stanley/.ssh/stanley_rsa stanely@host.example.com

    # make sure that no password is prompted.
    sudo su


SSH Troubleshooting
~~~~~~~~~~~~~~~~~~~~

* Validate that passwordless SSH configuration works fine for the destination. Assuming default user `stanley`:

    .. code-block:: bash

        sudo ssh -i /home/stanley/.ssh/stanley_rsa -t stanley@host.example.com uname -a


Configure Logging
-------------------
By default, the logs can be found in ``/var/log/st2``.

* With the standard logging setup you will notice files like ``st2*.log`` and ``st2*.audit.log`` in the log folder.

* Per component logging configuration can be found in ``/etc/st2*/logging.conf``. If you desire to change location of the log files the paths can be modified in these files.

* To configure logging with syslog, grab the configuration and follow instructions at :github_contrib:`st2contrib/extra/syslog </extra/syslog>`

* Check out LogStash configuration and Kibana dashboard for pretty logging and audit at :github_contrib:`st2contrib/extra/logstash </extra/logstash>`


.. include:: /engage.rst
