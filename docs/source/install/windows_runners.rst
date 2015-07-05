Windows Runners Configuration
=============================

.. note::

    Windows runners are currently in beta which means there might be rough edges
    and things might break.

    If you do encounter an issue, please get in touch and we will do our best to
    assist you.

Pre-requisites
--------------

Server which is running action runner service which is used for executing
Windows runners actions needs to have the following dependencies installed:

* ``smbclient`` >= 4.1 - Command line Samba client (``smbclient`` package on
  Ubuntu and ``samba-client`` package on Fedora).
* ``winexe`` >= 1.1 - Command line tool for executing commands remotely on
  Windows hosts.

Samba client is available in standard APT and Yum repositories and winexe is
available in our repositories. Both of those dependencies are installed by
default when using ``st2_deploy.sh`` script or a pupped based installation.

For information on configuring and enabling StackStorm repository, see
:ref:`stackstorm-repos`.

Installing on Ubuntu
~~~~~~~~~~~~~~~~~~~~

.. sourcecode:: bash

    sudo apt-get install smbclient winexe

Installing on Fedora
~~~~~~~~~~~~~~~~~~~~

.. sourcecode:: bash

    sudo yum install samba-client winexe

Supported Windows Versions
--------------------------

Windows runners have been tested on the following versions of Windows:

* Windows Server 2008
* Windows server 2012

Underlying library we use to talk to the Windows hosts also supports other
versions (2000 / XP / 2003 / Vista / 2008), but we haven't tested our
runners with those versions so we can't guarantee that runners will work there.

Configuring your Window Server for remote access
------------------------------------------------

For |st2| to be able to run actions on your Windows servers, you need to
configure them as described below.

Configuring the firewall
~~~~~~~~~~~~~~~~~~~~~~~~

For |st2| to be able to reach your server, you need to configure Windows
Firewall to allows traffic from the server where |st2| components (notably
action runner service) are running.

For safety reasons, you are encouraged to only allow traffic from |st2| server,
but if you want to allow traffic from all the IPs, you can run command listed
below in the command prompt:

.. sourcecode:: bash

    netsh firewall set service RemoteAdmin enable

Configuring the administrator user account
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

|st2| requires an administrator account on the Windows host where the actions
are executed to be able to upload and run the scripts there. By default, it
tries to use ``Administrator`` account to log in to your server.

Configuring the file share
~~~~~~~~~~~~~~~~~~~~~~~~~~

Windows script runner needs to upload a local PowerShell script to the remote server
before it can run it. For this to work, file sharing service (SMB - Samba) needs
to be enabled and you need to configure your firewall to allow traffic from the
|st2| IPs to the file sharing service ports.

In addition to that, you need to create a share where |st2| can upload the
script files. By default, |st2| tries to upload files to a share named ``C$``.
If this share is not available or you want to use a different share, you need
to specify ``share`` parameter when running a Windows script runner action.

Configuring PowerShell
~~~~~~~~~~~~~~~~~~~~~~
* Set the PowerShell execution policy to allow execution of the scripts. See <https://technet.microsoft.com/en-us/library/ee176961.aspx>
* Ensure that default ``powershell.exe`` is compatible with the script you are planning to run. To do so, open Command Prompet (``cmd``) on Windows machine, and run the following commands:

.. sourcecode:: bash

  C:\> powershell
  PS C:\> $PSVersionTable
  Name                           Value
  ----                           -----
  PSVersion                      4.0
  ...
  

Additional resources and links
------------------------------

* `Enable or Disable the File and Printer Sharing Firewall Rule <https://technet.microsoft.com/en-us/library/cc737069(v=ws.10).aspx>`_
* `Enable or Disable the Remote Desktop Firewall Rule <https://technet.microsoft.com/en-us/library/cc736451(v=ws.10).aspx>`_

.. include:: /engage.rst
