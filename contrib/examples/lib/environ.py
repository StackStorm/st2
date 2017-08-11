import os


def get_environ(env_var):
    val = os.environ.get(env_var, None)

    if not val:
        val = os.environ.get(env_var.lower(), os.environ.get(env_var.upper(), None))

    return val
