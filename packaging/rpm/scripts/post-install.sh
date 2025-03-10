set -e

# This %post scriptlet gets one argument, $1, the number of packages of
# this name that will be left on the system when this script completes. So:
#   * on install: $1 = 1
#   * on upgrade: $1 > 1
# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/#_syntax

# from %post in st2-packages.git/packages/st2/rpm/st2.spec
%service_post st2actionrunner st2api st2stream st2auth st2notifier st2workflowengine
%service_post st2rulesengine st2timersengine st2sensorcontainer st2garbagecollector
%service_post st2scheduler

# make sure that our socket generators run
systemctl daemon-reload >/dev/null 2>&1 || true
