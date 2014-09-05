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
