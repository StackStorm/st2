Docker
=================

::

    git clone https://github.com/StackStorm/st2express.git
    cd st2express/docker/
    docker build -t st2 .

This will install all |st2| components with Mistral workflow engine on Ubuntu 14.04 docker base image. There'll be some red output, don't worry about it. While waiting, check out |st2| :doc:`/video` for quick intro. Then run a docker container with the st2 image that just got built::

    docker run -it st2

Run /root/st2/start.sh inside the container to start all services including st2.

.. include:: on_complete.rst
