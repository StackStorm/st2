"""
"""
from oslo_config import cfg


class BaseMetricsDriver(object):
    """ Base class for driver implementations for metric collection
    """
    def time(self, key, time):
        """ Timer metric
        """
        pass

    def inc_counter(self, key, amount=1):
        """ Increment counter
        """
        pass

    def dec_counter(self, key, amount=1):
        """ Decrement metric
        """
        pass


def _get_metrics_driver():
    driver = cfg.CONF.metrics.driver

    if driver == "prometheus":
        from st2common.metrics.drivers.prometheus import PrometheusDriver
        driver_instance = PrometheusDriver()
    elif driver == "statsd":
        from st2common.metrics.drivers.statsd_driver import StatsdDriver
        driver_instance = StatsdDriver()
    else:
        driver_instance = None

    return driver_instance


if cfg.CONF.metrics.enable:
    METRICS = _get_metrics_driver()
