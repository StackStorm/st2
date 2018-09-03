# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import six
import psutil
import eventlet

from st2common import log as logging
from st2common.metrics.base import get_driver
from st2common.util.system_info import get_process_info

__all__ = [
    'PeriodicProcessMetricsReporter'
]

LOG = logging.getLogger(__name__)


class PeriodicProcessMetricsReporter(object):
    """
    Class for periodically reporting service / process level metrics (CPU, memory, IO) to the
    metrics backend server.
    """

    def __init__(self, report_interval=30):
        self._report_interval = report_interval

        self._process_info = get_process_info()
        self._started = False

    def start(self):
        LOG.debug('Starting process metrics reporting service')

        self._started = True

        while self._started:
            self._report_metrics()
            eventlet.sleep(self._report_interval)

    def stop(self):
        LOG.debug('Stopping process metrics reporting service')
        self._started = False

    def _report_metrics(self):
        """
        Reports metrics to the backend server.
        """
        metrics_driver = get_driver()

        # TODO: We should submit those as part of a single UDP packet
        metrics = self._get_metrics()

        LOG.debug('Submitting process level metrics to the metrics backend',
                  extra={'data': metrics})

        for key in ['cpu', 'memory', 'io']:
            items = metrics[key]

            for item_name, item_value in six.iteritems(items):
                # Skip empty / invalid values:
                if not item_value or item_value == 0.0:
                    continue

                # E.g. st2.st2api.1110.cpu.percentage
                metric_key = '%s.%s.%s.%s' % (self._process_info['name'],
                                              self._process_info['hostname'],
                                              self._process_info['pid'],
                                              item_name)
                metrics_driver.set_gauge(metric_key, item_value)

    def _get_metrics(self):
        """
        Retrieve various process related metrics.

        :rtype: ``dict``
        """
        p = psutil.Process()

        # st2.<service name>.<host>.<pid>.cpu.percentage
        data = {
            'name': None,
            'cpu': {
                'percentage': None,
                'system_time': None,
                'user_time': None
            },
            'memory': {
                'rss': None,
                'vms': None,
                'swap': None
            },
            'io': {
                'read_count': None,
                'write_count': None
            }
        }
        with p.oneshot():
            data['name'] = p.name()

            data['cpu']['percentage'] = p.cpu_percent()

            cpu_times = p.cpu_times()
            data['cpu']['system_time'] = cpu_times.system
            data['cpu']['user_time'] = cpu_times.user

            memory_info = p.memory_full_info()
            data['memory']['rss'] = memory_info.rss
            data['memory']['vms'] = memory_info.vms
            data['memory']['swap'] = memory_info.swap

            io_counters = p.io_counters()
            data['io']['read_count'] = io_counters.read_count
            data['io']['write_count'] = io_counters.write_count

        return data
