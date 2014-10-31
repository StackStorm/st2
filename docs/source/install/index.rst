Installation
=================

To install and run StackStorm |st2| on Ubuntu/Debian or RedHat/Fedora with all dependencies,
download and run the deployment script.

::

    curl -q -k -O https://ops.stackstorm.net/releases/st2/scripts/st2_deploy.sh
    chmod +x st2_deploy.sh
    sudo ./st2_deploy.sh

This will download and install the latest release of StackStorm (currently |release|). Installation should take about 5 min. Grab a coffee and watch :doc:`/video` while it is being installed.

.. include:: on_complete.rst

.. rubric:: More Installations

.. toctree::
    :maxdepth: 1

    Ubuntu / Debian <deb>
    RedHat / Fedora <rpm>
    config
    Vagrant <vagrant>
    docker
    deploy
    sources


.. note::
  We compile, build and test on Fedora 20 and Ubuntu 14.04. The `st2_deploy.sh <https://github.com/StackStorm/st2sandbox/blob/master/scripts/deploy_stan.sh>`_ script should work for other versions, but if you find a problem, let us know. Fixes welcome :)