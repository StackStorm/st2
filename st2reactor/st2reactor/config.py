from oslo.config import cfg

import st2common.config as common_config
common_config.register_opts()

CONF = cfg.CONF


def _register_common_opts():
    common_config.register_opts()


def _register_reactor_opts():
    logging_opts = [
        cfg.StrOpt('logging', default='etc/logging.conf',
                   help='location of the logging.conf file')
    ]
    CONF.register_opts(logging_opts, group='reactor')

    sensors_opts = [
        cfg.StrOpt('system_path', default='st2reactor/st2reactor/contrib/sensors',
                   help='path to load system sensor modules from')
    ]
    CONF.register_opts(sensors_opts, group='sensors')

    sensor_test_opt = cfg.StrOpt('sensor-path', help='Path to the sensor to test.')
    CONF.register_cli_opt(sensor_test_opt)

    reactor_opts = [
        cfg.StrOpt('actionexecution_base_url', default='http://0.0.0.0:9101/actionexecutions',
                   help='URL of POSTing to the actionexecution endpoint.')
    ]
    CONF.register_opts(reactor_opts, group='reactor')

    st2_webhook_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='Host for the st2 webhook endpoint.'),
        cfg.IntOpt('port', default='6000', help='Port for the st2 webhook endpoint.'),
        cfg.StrOpt('url', default='/webhooks/st2/', help='URL of the st2 webhook endpoint.')
    ]
    CONF.register_opts(st2_webhook_opts, group='st2_webhook_sensor')

    generic_webhook_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='Host for the generic webhook endpoint.'),
        cfg.IntOpt('port', default='6001', help='Port for the generic webhook endpoint.'),
        cfg.StrOpt('url', default='/webhooks/generic/', help='URL of the st2 webhook endpoint.')
    ]
    CONF.register_opts(generic_webhook_opts, group='generic_webhook_sensor')


def register_opts():
    _register_common_opts()
    _register_reactor_opts()


register_opts()


def parse_args(args=None):
    CONF(args=args)
