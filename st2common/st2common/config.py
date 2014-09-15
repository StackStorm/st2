from oslo.config import cfg


def _do_register_opts(opts, group, ignore_errors):
    try:
        cfg.CONF.register_opts(opts, group=group)
    except:
        if not ignore_errors:
            raise


def register_opts(ignore_errors=False):

    auth_opts = [
        cfg.BoolOpt('enable', default=True, help='Enable authentication middleware.')
    ]
    _do_register_opts(auth_opts, 'auth', ignore_errors)

    schema_opts = [
        cfg.IntOpt('version', default=4, help='Version of JSON schema to use.'),
        cfg.StrOpt('draft', default='http://json-schema.org/draft-04/schema#',
                   help='URL to the JSON schema draft.')
    ]
    _do_register_opts(schema_opts, 'schema', ignore_errors)

    content_opts = [
        cfg.StrOpt('content_pack_path', default='/opt/stackstorm/',
                   help='path to load sensor modules from')
    ]
    _do_register_opts(content_opts, 'content', ignore_errors)

    db_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='host of db server'),
        cfg.IntOpt('port', default=27017, help='port of db server'),
        cfg.StrOpt('db_name', default='st2', help='name of database')
    ]
    _do_register_opts(db_opts, 'database', ignore_errors)

    actions_opts = [
        cfg.StrOpt('modules_path', default='/opt/stackstorm/actions',
                   help='path where action plugins are located')
    ]
    _do_register_opts(actions_opts, 'actions', ignore_errors)

    rules_opts = [
        cfg.StrOpt('rules_path', default='/opt/stackstorm/rules',
                   help='path to load rule files')
    ]
    _do_register_opts(rules_opts, 'rules', ignore_errors)

    messaging_opts = [
        cfg.StrOpt('url', default='amqp://guest:guest@localhost:5672//',
                   help='URL of the messaging server.')
    ]
    _do_register_opts(messaging_opts, 'messaging', ignore_errors)

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
