"""
"""
from prometheus_client import Histogram, Counter

from st2common.metrics.metrics import BaseMetricsDriver


class PrometheusDriver(BaseMetricsDriver):
    """ Base class for driver implementations for metric collection
    """
    def __init__(self):
        pass

    def time(self, key, time):
        """ Timer metric
        """
        prometheus_histogram = Histogram(key)
        prometheus_histogram.observe(time)

    def inc_counter(self, key, amount=1):
        """ Increment counter
        """
        prometheus_counter = Counter(key)
        prometheus_counter.inc(amount)

    def dec_counter(self, key, amount=1):
        """ Decrement metric
        """
        prometheus_counter = Counter(key)
        prometheus_counter.dec(amount)
