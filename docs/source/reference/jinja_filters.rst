Jinja Filters
=============

StackStorm supports `Jinja2 variable templating <http://jinja.pocoo.org/docs/dev/templates/#variables>`__
in Rules, Action Chains and Actions etc. Jinja2 templates support `filters <http://jinja.pocoo.org/docs/dev/templates/#list-of-builtin-filters>`__ to allow some advanced capabilities in working with variables. StackStorm has further
added some more filters.

Filters with regex support
^^^^^^^^^^^^^^^^^^^^^^^^^^
Makes it possible to use regex to search, match and replace in expressions.

regex_match
~~~~~~~~~~~
match pattern at the beginning of expression.

.. code-block:: bash

    {{value_key | regex_match('x')}}
    {{value_key | regex_match("^v(\\d+\\.)?(\\d+\\.)?(\\*|\\d+)$")}}

regex_replace
~~~~~~~~~~~~~
replace a pattern matching regex with supplied value (backreferences possible)

.. code-block:: bash

    {{value_key | regex_replace("x", "y")}}
    {{value_key | regex_replace("(blue|white|red)", "beautiful color \\1")}}

regex_search
~~~~~~~~~~~~
search pattern anywhere is supplied expression

.. code-block:: bash

    {{value_key | regex_search("y")}}
    {{value_key | regex_search("^v(\\d+\\.)?(\\d+\\.)?(\\*|\\d+)$")}}


Filters to work with version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Filters that work with `semver <http://semver.org>`__ formatted version string.

version_compare
~~~~~~~~~~~~~~~
compares expression with supplied value and return -1, 0 and 1 for less than, equal and more than respectively

.. code-block:: bash

    {{version | version_compare("0.10.1")}}

version_more_than
~~~~~~~~~~~~~~~~~
True if version is more than supplied value

.. code-block:: bash

    {{version | version_more_than("0.10.1")}}

version_less_than
~~~~~~~~~~~~~~~~~
True if version is less than supplied value

.. code-block:: bash

    {{version | version_less_than("0.9.2")}}

version_equal
~~~~~~~~~~~~~
True if versions are of equal value

.. code-block:: bash

    {{version | version_less_than("0.10.0")}}

version_match
~~~~~~~~~~~~~
True if versions match. Supports operators >,<, ==, <=, >=.

.. code-block:: bash

    {{version | version_match(">0.10.0")}}


version_bump_major
~~~~~~~~~~~~~~~~~~
Bumps up the major version of supplied version field

.. code-block:: bash

    {{version | version_bump_major}}

version_bump_minor
~~~~~~~~~~~~~~~~~~
Bumps up the minor version of supplied version field

.. code-block:: bash

    {{version | version_bump_minor}}

version_bump_patch
~~~~~~~~~~~~~~~~~~
Bumps up the patch version of supplied version field

.. code-block:: bash

    {{version | version_bump_patch}}

version_strip_patch
~~~~~~~~~~~~~~~~~~~
Drops patch version of supplied version field

.. code-block:: bash

    {{version | version_strip_patch}}
