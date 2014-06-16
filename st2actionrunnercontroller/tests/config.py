# Server Specific Configurations
# TODO: externalize port number to a value stored in st2common
server = {
    'port': '9501',
    'host': '0.0.0.0'
}

# Pecan Application Configurations
app = {
    'root': 'st2actionrunnercontroller.controllers.root.RootController',
    'modules': ['st2actionrunnercontroller'],
    'static_root': '%(confdir)s/../../public',
    'template_path': '%(confdir)s/../templates',
    'debug': True,
    'errors': {
        '404': '/error/404',
        '__force_dict__': True
    }
}

# Custom Configurations must be in Python dictionary format::
#
# foo = {'bar':'baz'}
#
# All configurations are accessible at::
# pecan.conf
