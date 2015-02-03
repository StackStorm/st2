Docker
======

st2express repository contains a Dockerfile which allows you to easily and
quickly run all the |st2| components inside a single docker container.

All the services are running inside a single docker container which means
this method is great for testing and developing |st2|, but not appropriate
for production where "one service per container" model should be followed.

::

    git clone https://github.com/StackStorm/st2express.git
    cd st2express/docker/
    docker build -t st2 .

This will install all |st2| components with Mistral workflow engine on Ubuntu
14.04 docker base image. There'll be some red output, don't worry about it.
While waiting, check out |st2| :doc:`/video` for quick intro. Then run a docker
container with the st2 image that just got built

::

    docker run -it st2

Run ``/root/st2/start.sh`` inside the container to start all services including
st2.

For more information, please refer to the `README <https://github.com/StackStorm/st2express/tree/master/docker>`_
inside the st2express repository.

.. include:: on_complete.rst
