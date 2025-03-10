set -e

# from %preun in st2-packages.git/packages/st2/rpm/st2.spec
%service_preun st2actionrunner %{worker_name} st2api st2stream st2auth st2notifier st2workflowengine
%service_preun st2rulesengine st2timersengine st2sensorcontainer st2garbagecollector
%service_preun st2scheduler
