Scripted Installer
==================

.. TODO:: Move deploy script aka st2_deploy.sh instructions here. Put a deprecation note and reference to new installer.


To install and run |st2| on a single Ubuntu/Debian or RedHat/Fedora box, with all dependencies,
download and run the deployment script.

::

    curl -q -k -O https://downloads.stackstorm.net/releases/st2/scripts/st2_deploy.sh
    chmod +x st2_deploy.sh
    sudo ./st2_deploy.sh

This will download and install the stable release of |st2| (currently |release|).
If you want to install the latest development version, run ``sudo ./st2_deploy.sh latest``.
Installation should take about 5 min. Grab a coffee and watch :doc:`/video` while it is being installed.

At the end of the installation, you will see a nice big **ST2 OK**, the default username and password,
and WebUI url:

::

    WebUI at http://my-host:8080/
    ==========================================

              _   ___     ____  _  __
             | | |__ \   / __ \| |/ /
          ___| |_   ) | | |  | | ' /
         / __| __| / /  | |  | |  <
         \__ \ |_ / /_  | |__| | . \
         |___/\__|____|  \____/|_|\_\

      st2 is installed and ready to use.
    ==========================================

    Test StackStorm user account details

    Username: testu
    Password: testp

    Test account credentials were also written to the default CLI config at .

    To login and obtain an authentication token, run the following command:

    st2 auth testu -p testp

.. include:: on_complete.rst