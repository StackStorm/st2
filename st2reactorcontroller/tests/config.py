from oslo.config import cfg

CONF = cfg.CONF

db_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='host of db server'),
    cfg.IntOpt('port', default=27017, help='port of db server'),
    cfg.StrOpt('db_name', default='st2', help='name of database')
]
CONF.register_opts(db_opts, group='database')

api_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='stackaton API server host'),
    cfg.IntOpt('port', default=9102, help='stackaton API server port')
]
CONF.register_opts(api_opts, group='reactor_controller_api')

# note : template_path value only works if started from the top-level of the codebase. Brittle!
pecan_opts = [
    cfg.StrOpt('root',
               default='st2reactorcontroller.controllers.root.RootController',
               help='Pecan root controller'),
    cfg.StrOpt('template_path',
               default='%(confdir)s/st2reactorcontroller/st2reactorcontroller/templates'),
    cfg.ListOpt('modules', default=['st2reactorcontroller']),
    cfg.BoolOpt('debug', default=True),
    cfg.BoolOpt('auth_enable', default=True),
    cfg.DictOpt('errors', default={404: '/error/404', '__force_dict__': True})
]
CONF.register_opts(pecan_opts, group='reactor_pecan')


def parse_args():
    CONF(args=[])
