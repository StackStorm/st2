import six


def replace_dot_in_key(d):
    if not isinstance(d, dict):
        return d
    for oldkey, value in six.iteritems(d):
        value = replace_dot_in_key(value)
        newkey = oldkey.replace('.', u'\u2024')
        if oldkey != newkey:
            d[newkey] = value
            del d[oldkey]
    return d


def replace_u2024_in_key(d):
    if not isinstance(d, dict):
        return d
    for oldkey, value in six.iteritems(d):
        value = replace_u2024_in_key(value)
        newkey = oldkey.replace(u'\u2024', '.')
        if oldkey != newkey:
            d[newkey] = value
            del d[oldkey]
    return d
