"""
Plugin which tells Pylint how to handle classes which define attributes using jsonschema
in "schema" class attribute.

Those classes dyamically assign attributes defined in the schema on the class inside the
constructor.
"""

from astroid import MANAGER
from astroid import scoped_nodes


def register(linter):
    pass


def transform(cls):
    if cls.name.endswith('API') or 'schema' in cls.locals:
        # This is a class which defines attributes in "schema" variable using json schema.
        # Those attributes are then assigned during run time inside the constructor

        fqdn = cls.qname()
        module_name, class_name = fqdn.rsplit('.', 1)

        module = __import__(module_name, fromlist=[class_name])
        actual_cls = getattr(module, class_name)

        schema = actual_cls.schema

        if not isinstance(schema, dict):
            # Not a class we are interested in
            return

        properties = schema.get('properties', {}).keys()

        for property_name in properties:
            cls.locals[property_name] = [scoped_nodes.Class(property_name, None)]


MANAGER.register_transform(scoped_nodes.Class, transform)
