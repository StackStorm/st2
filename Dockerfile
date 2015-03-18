FROM ubuntu
WORKDIR /code
RUN apt-get update && apt-get -y install \
  python-pip \
  build-essential \
  python-dev \
  screen \
  git
RUN pip install virtualenv nose
ADD . /code
RUN make virtualenv && . /code/virtualenv/bin/activate && pip install -r requirements.txt && pip install -r test-requirements.txt
RUN mkdir -p /opt/stackstorm/packs/
CMD /sbin/ip route|awk '/default/ { print  $3,"\tdockerhost" }' >> /etc/hosts && DOCKER_COMPOSE=1 ST2_CONF=/code/conf/st2-docker.conf /code/tools/launchdev.sh startclean
