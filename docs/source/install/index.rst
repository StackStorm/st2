Installation
============

There are several methods to deploy StackStorm. The easiest is all-in-one install
on Ubuntu/Debian or RedHat/CentOS. Skip below if you want to learn about
:doc:`puppet` or :doc:`chef`, or other installations approaches.


.. note:: To install Enterprise Edition, enter your license key when prompted by graphical setup, or place it in the anwser file for unattended installation. To receive a key, request a free trial or obtain a license at `stackstorm.com/product <stackstorm.com/product/#enterprise>`_. If no license provided, StackStorm Community will be installed.


To install and run |st2| on a single Ubuntu/Debian or RedHat/CentOS box, with all dependencies,
run the bootstrap script:

::

    curl -sSL http://stackstorm.com/install.sh | sudo sh

You will need elevated privileges in order to run this script. This will download and deploy the stable release of |st2| (currently |release|). Check out :doc:`all_in_one` to learn how to provide answer file, get latest development version, and other details. Installation should take about 20 min. *Yes, we are working on making it faster!* Grab a coffee and watch :doc:`/video` while it is being installed. Once completed, you will see the following console output. Read it :)

::

    ███████╗████████╗██████╗      ██████╗ ██╗  ██╗
    ██╔════╝╚══██╔══╝╚════██╗    ██╔═══██╗██║ ██╔╝
    ███████╗   ██║    █████╔╝    ██║   ██║█████╔╝
    ╚════██║   ██║   ██╔═══╝     ██║   ██║██╔═██╗
    ███████║   ██║   ███████╗    ╚██████╔╝██║  ██╗
    ╚══════╝   ╚═╝   ╚══════╝     ╚═════╝ ╚═╝  ╚═╝

      st2 is installed and ready to use.

    First time starting this machine up?
    Visit https://kickbox.example.com/setup to configure StackStorm
    Otherwise, head to https://kickbox.example.com to access the WebUI

    If you would like to use the CLI interface, you will need
    to ensure that StackStorm environment variables are properly
    set. You can do this by logging out and logging back in, or
    running the command:

    . /etc/profile.d/st2.sh


Visit the setup URL output, ``https://<HOST>/setup`` and proceed to :ref:`all_in_one-running_the_setup` to configure StackStorm and complete installation.

.. include:: on_complete.rst

.. note:: The :doc:`st2_deploy` which was a primary way to deploy up to v0.13 is available, although being deprecated by the new :doc:`all_in_one`

.. rubric:: More Installations

.. toctree::
    :maxdepth: 1

    All-In-One Installer  <all_in_one>
    Ubuntu / Debian <deb>
    RedHat / CentOS <rpm>
    Scripted Installer <st2_deploy>
    Vagrant <vagrant>
    Docker <docker>
    Puppet <puppet>
    chef
    Ansible <ansible>
    salt
    sources

