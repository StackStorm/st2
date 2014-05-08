from oslo.config import cfg

CONF = cfg.CONF

db_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='host of db server'),
    cfg.IntOpt('port', default=27017, help='port of db server'),
    cfg.StrOpt('db_name', default='kandra', help='name of database')
]
CONF.register_opts(db_opts, group='database')


def parse_args():
    CONF(args=[])