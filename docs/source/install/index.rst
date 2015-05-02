Installation
============

To install and run |st2| on Ubuntu/Debian or RedHat/Fedora with all dependencies,
download and run the deployment script.

::

    curl -q -k -O https://downloads.stackstorm.net/releases/st2/scripts/st2_deploy.sh
    chmod +x st2_deploy.sh
    sudo ./st2_deploy.sh

This will download and install the stable release of |st2| (currently |release|).
If you want to install the latest development version, run ``sudo ./st2_deploy.sh latest``.
Installation should take about 5 min. Grab a coffee and watch :doc:`/video` while it is being installed.

.. include:: on_complete.rst

.. rubric:: More Installations

.. toctree::
    :maxdepth: 1

    Ubuntu / Debian <deb>
    RedHat / Fedora <rpm>
    Vagrant <vagrant>
    Docker <docker>
    sources
    config
    webui
    windows_runners
    StackStorm Repositories <stackstorm_repos>

.. note::
    We compile, build and test on Fedora 20 and Ubuntu 14.04. The `st2_deploy.sh <https://github.com/StackStorm/st2sandbox/blob/master/scripts/st2_deploy.sh>`_ 
    script should work for other versions, but if you find a problem, let us know. Fixes welcome :)
  
    st2_deploy.sh script allows you to easily install and run |st2| with all the
    dependencies on a single server. It's only intented to be used for testing,
    evaluation and demonstration purposes (it doesn't use HTTPS, it uses flat file
    htpasswd based authentication, etc.) - you should **not** use it for production
    deployments.

    For production deployments you follow deb / rpm installation methods, or use our puppet modules.
