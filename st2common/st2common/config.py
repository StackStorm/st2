from oslo.config import cfg


def register_opts():
    schema_opts = [
        cfg.IntOpt('version', default=4, help='Version of JSON schema to use.'),
        cfg.StrOpt('draft', default='http://json-schema.org/draft-04/schema#',
                   help='URL to the JSON schema draft.')
    ]

    cfg.CONF.register_opts(schema_opts, group='schema')

    content_opts = [
        cfg.StrOpt('content_pack_path', default='/opt/stackstorm/',
                   help='path to load sensor modules from')
    ]
    cfg.CONF.register_opts(content_opts, group='content')

    db_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='host of db server'),
        cfg.IntOpt('port', default=27017, help='port of db server'),
        cfg.StrOpt('db_name', default='st2', help='name of database')
    ]
    cfg.CONF.register_opts(db_opts, group='database')

    logging_opts = [
        cfg.StrOpt('config_file', default='conf/logging.conf',
                   help='location of the logging.conf file')
    ]
    cfg.CONF.register_opts(logging_opts, group='common_logging')

    actions_opts = [
        cfg.StrOpt('modules_path', default='/opt/stackstorm/actions',
                   help='path where action plugins are located')
    ]
    cfg.CONF.register_opts(actions_opts, group='actions')

    rules_opts = [
        cfg.StrOpt('rules_path', default='/opt/stackstorm/rules',
                   help='path to load rule files')
    ]
    cfg.CONF.register_opts(rules_opts, group='rules')


def parse_args(args=None):
    register_opts()
    cfg.CONF(args=args)
