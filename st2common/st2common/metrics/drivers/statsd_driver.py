"""
"""
from oslo_config import cfg
import statsd

from st2common.metrics.metrics import BaseMetricsDriver


class StatsdDriver(BaseMetricsDriver):
    """ StatsD Implementation of the metrics driver
    """
    def __init__(self):
        self._connection = statsd.StatsClient(cfg.CONF.metrics.host, cfg.CONF.metrics.port)

    def time(self, key, time):
        """ Timer metric
        """
        self._connection.timing(key, time)

    def inc_counter(self, key, amount=1):
        """ Increment counter
        """
        self._connection.incr(key, amount)

    def dec_counter(self, key, amount=1):
        """ Decrement metric
        """
        self._connection.decr(key, amount)
