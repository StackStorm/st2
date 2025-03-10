set -e

# from %postun in st2-packages.git/packages/st2/rpm/st2.spec
%service_postun st2actionrunner %{worker_name} st2api st2stream st2auth st2notifier st2workflowengine
%service_postun st2rulesengine st2timersengine st2sensorcontainer st2garbagecollector
%service_postun st2scheduler

# Remove st2 logrotate config, since there's no analog of apt-get purge available
if [ $1 -eq 0 ]; then
    rm -f /etc/logrotate.d/st2
fi
