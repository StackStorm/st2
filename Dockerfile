FROM ubuntu
WORKDIR /code
RUN apt-get update && apt-get -y install python-pip screen git build-essential python-dev
RUN pip install virtualenv nose
ADD . /code
RUN make virtualenv && . /code/virtualenv/bin/activate && pip install -r requirements.txt && pip install -r test-requirements.txt
RUN mkdir -p /opt/stackstorm/packs/
CMD DOCKER_COMPOSE=1 /code/tools/launchdev.sh startclean
