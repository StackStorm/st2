Installation
============
There are a few methods to deploys StackStorm. The easiest is all-in-one install
on Ubuntu/Debian or RedHat/Fedora which we explain next. Skip below if you want to learn about
:doc:`docker` or :doc:`vagrant`, or other installations approaches.

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

.. rubric:: More Installations

.. toctree::
    :maxdepth: 1

    Ubuntu / Debian <deb>
    RedHat / Fedora <rpm>
    Vagrant <vagrant>
    Docker <docker>
    Puppet <puppet>
    sources
    config
    webui
    windows_runners
    StackStorm Repositories <stackstorm_repos>

.. note::
    We compile, build and test on Fedora 20 and Ubuntu 14.04. The `st2_deploy.sh <https://github.com/StackStorm/st2sandbox/blob/master/scripts/st2_deploy.sh>`_
    script should work for other versions, but if you find a problem, let us know. Fixes welcome :)

    st2_deploy.sh script allows you to easily install and run |st2| with all the
    dependencies on a single server. It's intended to be used for testing,
    evaluation and POC. It doesn't use HTTPS, uses flat file
    htpasswd based authentication, etc. - you should **not** use it 'as is' for production
    deployments.

    For production deployments follow deb / rpm installation methods, or use our puppet modules.
