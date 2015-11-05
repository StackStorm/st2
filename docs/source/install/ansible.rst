Ansible
=============
Ansible playbooks to install |st2|.

Allows you to deploy and further configure |st2| installation on local or remote machines with Ansible configuration management tool.
Playbooks source code is available as GitHub repository `ansible-st2
<https://github.com/StackStorm/ansible-st2>`_.

---------------------------

Supported platforms
---------------------------
* Ubuntu 12.04 LTS
* Ubuntu 14.04 LTS

Requirements
---------------------------
At least 2GB of memory and 3.5GB of disk space is required, since StackStorm is shipped with RabbitMQ, MySQL, Mongo, OpenStack Mistral and dozens of Python dependencies.

Installation
---------------------------
.. sourcecode:: bash

    git clone https://github.com/StackStorm/ansible-st2.git
    cd ansible-st2

    ansible-playbook playbooks/st2express.yaml


Variables
---------------------------
Below is the list of variables you can redefine in your playbook to customize st2 deployment:

+------------------------+-----------------+--------------------------------------------------------------------------+
| Variable               | Default         | Description                                                              |
+========================+=================+==========================================================================+
| ``st2_version``        | ``stable``      | StackStorm version to install. Latest ``stable``, ``unstable``           |
|                        |                 | to get automatic updates or pin it to numeric version like ``0.12.1``.   |
+------------------------+-----------------+--------------------------------------------------------------------------+
| ``st2_revision``       | ``current``     | StackStorm revision to install. ``current`` to get the                   |
|                        |                 | latest build (autoupdating) or pin it to numeric build like ``6``.       |
+------------------------+-----------------+--------------------------------------------------------------------------+
| ``st2_action_runners`` | # vCPUs         | Number of action runner workers to start.                                |
|                        |                 | Defaults to number of machine vCPUs, but not less than ``2``.            |
+------------------------+-----------------+--------------------------------------------------------------------------+
| ``st2_system_user``    | ``stanley``     | System user on whose behalf st2 would work,                              |
|                        |                 | including remote/local action runners.                                   |
+------------------------+-----------------+--------------------------------------------------------------------------+
| ``st2_auth_username``  | ``testu``       | Username used by StackStorm standalone authentication.                   |
+------------------------+-----------------+--------------------------------------------------------------------------+
| ``st2_auth_password``  | ``testp``       | Password used by StackStorm standalone authentication.                   |
+------------------------+-----------------+--------------------------------------------------------------------------+

Examples
---------------------------
Install ``stable`` StackStorm with all its components on local machine:

.. sourcecode:: bash

    ansible-playbook playbooks/st2express.yaml -i 'localhost,' --connection=local


.. note::

    Keeping ``stable`` version is useful to update StackStorm by re-running playbook, since it will reinstall |st2| if there is new version available.
    This is default behavior. If you don't want updates - consider pinning version numbers.

Install specific numeric version of st2 with pinned revision number as well:

.. sourcecode:: bash

    ansible-playbook playbooks/st2express.yaml --extra-vars='st2_version=0.12.2 st2_revision=6'

or latest unstable (development branch):

.. sourcecode:: bash

    ansible-playbook playbooks/st2express.yaml --extra-vars='st2_version=unstable'

