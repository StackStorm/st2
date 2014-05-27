# Server Specific Configurations
# TODO: externalize port number to a file in st2common
server = {
    'port': '9101',
    'host': '0.0.0.0'
}

# Pecan Application Configurations
app = {
    'root': 'st2actioncontroller.controllers.root.RootController',
    'modules': ['st2actioncontroller'],
    'default_renderer' : 'json',
    'static_root': '%(confdir)s/public',
    'template_path': '%(confdir)s/st2actioncontroller/templates',
    'debug': True,
    'errors': {
        404: '/error/404',
        '__force_dict__': True
    }
}

logging = {
    'loggers': {
        'root': {'level': 'INFO', 'handlers': ['console']},
        'st2actioncontroller': {'level': 'DEBUG', 'handlers': ['console']}
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'formatters': {
        'simple': {
            'format': ('%(asctime)s %(levelname)-5.5s [%(name)s]'
                       '[%(threadName)s] %(message)s')
        }
    }
}

# Custom Configurations must be in Python dictionary format::
#
# foo = {'bar':'baz'}
#
# All configurations are accessible at::
# pecan.conf
