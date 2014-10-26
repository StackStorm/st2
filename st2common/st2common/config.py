from oslo.config import cfg


def _do_register_opts(opts, group, ignore_errors):
    try:
        cfg.CONF.register_opts(opts, group=group)
    except:
        if not ignore_errors:
            raise


def register_opts(ignore_errors=False):

    auth_opts = [
        cfg.BoolOpt('enable', default=True, help='Enable authentication middleware.'),
        cfg.IntOpt('token_ttl', default=86400, help='Access token ttl in seconds.')
    ]
    _do_register_opts(auth_opts, 'auth', ignore_errors)

    system_user_opts = [
        cfg.StrOpt('user',
                   default='stanley',
                   help='Default system user.'),
        cfg.StrOpt('ssh_key_file',
                   default='/home/vagrant/.ssh/stanley_rsa',
                   help='SSH private key for the system user.')
    ]
    _do_register_opts(system_user_opts, 'system_user', ignore_errors)

    schema_opts = [
        cfg.IntOpt('version', default=4, help='Version of JSON schema to use.'),
        cfg.StrOpt('draft', default='http://json-schema.org/draft-04/schema#',
                   help='URL to the JSON schema draft.')
    ]
    _do_register_opts(schema_opts, 'schema', ignore_errors)

    content_opts = [
        cfg.StrOpt('packs_base_path', default='/opt/stackstorm/',
                   help='path to load sensor modules from'),
        cfg.StrOpt('system_path', default='st2reactor/st2reactor/contrib/sensors',
                   help='path to load system sensor modules from')
    ]
    _do_register_opts(content_opts, 'content', ignore_errors)

    db_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='host of db server'),
        cfg.IntOpt('port', default=27017, help='port of db server'),
        cfg.StrOpt('db_name', default='st2', help='name of database'),
        cfg.StrOpt('username', help='username for db login'),
        cfg.StrOpt('password', help='password for db login'),
    ]
    _do_register_opts(db_opts, 'database', ignore_errors)

    messaging_opts = [
        cfg.StrOpt('url', default='amqp://guest:guest@localhost:5672//',
                   help='URL of the messaging server.')
    ]
    _do_register_opts(messaging_opts, 'messaging', ignore_errors)

    syslog_opts = [
        cfg.StrOpt('host', default='localhost',
                   help='Host for the syslog server.'),
        cfg.IntOpt('port', default=514,
                   help='Port for the syslog server.'),
        cfg.StrOpt('facility', default='local7',
                   help='Syslog facility level.')
    ]
    _do_register_opts(syslog_opts, 'syslog', ignore_errors)

    use_debugger = cfg.BoolOpt(
        'use-debugger', default=True,
        help='Enables debugger. Note that using this option changes how the '
             'eventlet library is used to support async IO. This could result in '
             'failures that do not occur under normal operation.'
    )
    cfg.CONF.register_cli_opt(use_debugger)


def parse_args(args=None):
    register_opts()
    cfg.CONF(args=args)
