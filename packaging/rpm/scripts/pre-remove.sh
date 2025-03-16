set -e

# This %preun scriptlet gets one argument, $1, the number of packages of
# this name that will be left on the system when this script completes. So:
#   * on upgrade:   $1 > 0
#   * on uninstall: $1 = 0
# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/#_syntax

# from %preun in st2-packages.git/packages/st2/rpm/st2.spec
%service_preun st2actionrunner %{worker_name} st2api st2stream st2auth st2notifier st2workflowengine
%service_preun st2rulesengine st2timersengine st2sensorcontainer st2garbagecollector
%service_preun st2scheduler
