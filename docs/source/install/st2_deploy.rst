Scripted Installer
==================

.. warning::

    Scripted installer is being replaced with production-ready :doc:`all_in_one`.

    We still compile, build, test on CentOS 6, CentOS 7, and Ubuntu 14.04 and keep it around as a back stop
    for those who can't use :doc:`all_in_one` for some reasons. Be aware that it is s **not intended for production:** no HTTPS, flat file htpasswd based authentication, running web services in built-in simple-http-service, etc. The code is available at `st2_deploy.sh <https://github.com/StackStorm/st2sandbox/blob/master/scripts/st2_deploy.sh>`_.

    Note that the documentation has been updated assuming :doc:`all_in_one` in mind. For some `st2_deploy.sh` specific deployment configurations you may need to look at `Docs for v0.13 <http://docs.stackstorm.com/0.13/>`_

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


For production deployments use :doc:`all_in_one`, follow deb / rpm installation methods, or leverage puppet modules from `puppet-st2 <https://github.com/StackStorm/puppet-st2>`_.
