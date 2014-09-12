from st2auth.controllers import access


class RootController(object):
    tokens = access.TokenController()
