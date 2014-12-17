Authentication Service
======================

st2auth service is responsible for handling user authentication and generating
user-scoped temporary access tokens. Those access tokens are used to
authenticate against the st2api service.

The service can run in two different modes which are described bellow.

Configuring the service
-----------------------

The service can be configured via the config file or via the command line
arguments.

.. note::

    When the options are specified via the command line arguments, you need to
    prefix them with ``auth-``. For example
    ``st2auth --auth-mode=standalone ...``

The available options are described bellow:

* ``host`` - Hostname for the service to listen on.
* ``port`` - Port for the service to listen on.
* ``secure`` - True to use SSL / TLS.
* ``cert`` - Path to the certificate file. Only used when secure is True.
* ``key`` - Path to the private key file. Only used when secure is True.
* ``mode`` - Mode to use (``proxy`` or ``standalone``)
* ``backend_kwargs`` - JSON serialized keyword arguments which are passed to
  the authentication backend.

Proxy mode
----------

In the proxy mode which is a default, authentication is handled upstream from
the st2auth service.

.. figure:: /_static/images/st2auth_proxy_mode.png
    :align: center

    Proxy mode

The service upstream is responsible for performing the authentication. If the
provided credentials are correct, the service needs to populate ``REMOTE_USER``
environment variable and proxy the request to the st2auth service. The
st2auth service then generates a new access token and returns it back to the
user.

An example of a service which can perform authentication upstream includes
Apache httpd, Nginx and load balancer.

If you are using Apache, this means you can utilize one of the many
`authentication modules <http://httpd.apache.org/docs/2.2/howto/auth.html>`_
supported by Apache httpd (e.g. basic auth, PAM module, kerberos module, etc.).

When you are running authentication service in the proxy mode, you need to make
sure the service is only accessible to the upstream service which is responsible
for handling authentication.

This usually means running the upstream service on the same host as the
st2auth service and configuring it to only listen on ``localhost``. As an
alternative, you can run upstream service on a different host inside the same
private network and configure the st2auth service to listen on an internal IP
and configure the firewall on that host so only the upstream service can reach
it.

Standalone mode
---------------

In the standalone mode, st2auth service handles the authentication itself
using a backend which is specified in the config file.

.. figure:: /_static/images/st2auth_standalone_mode.png
    :align: center

    Standalone mode

In this mode, the service should listen on https (this means setting the
``secure`` configuration option) and be accessible to the st2 clients.

Authentication backends
-----------------------

Flat file backend
~~~~~~~~~~~~~~~~~

Flat file backend supports reading credentials from an Apache HTTPd htpasswd
formatted file. To manage this file you can use `htpasswd`_ utility which comes
with a standard Apache httpd distribution.

Configuration options
^^^^^^^^^^^^^^^^^^^^^

* ``file_path`` - Path to the file containing credentials.

Example usage
^^^^^^^^^^^^^^

.. sourcecode:: bash

    st2auth --config-file /etc/stanley/st2.conf --auth-secure --auth-mode=standalone \
        --auth-backend=flat_file --auth-backend_kwargs='{"file_path": "/etc/private/htpaswd"}'

MongoDB backend
~~~~~~~~~~~~~~~

MongoDB backend supports reading credentials from a MongoDB collection called
``users``.

Entries in this collection need to have the following attributes:

* ``username`` - Username
* ``salt`` - Salt for the password.
* ``password`` - SHA256 hash for the salt+password - SHA256(<salt><password>)

Configuration options
^^^^^^^^^^^^^^^^^^^^^

* ``db_host`` - MongoDB server host.
* ``db_port`` - MongoDB server port.
* ``db_name`` - Name of the database to use.

Example usage
^^^^^^^^^^^^^^

.. sourcecode:: bash

    st2auth --config-file /etc/stanley/st2.conf --auth-secure --auth-mode=standalone \
        --auth-backend=mongodb \
        --auth-backend_kwargs='{"db_host": "196.168.100.10", "db_port": 27017, "db_name": "st2auth"}'


.. _htpasswd: https://httpd.apache.org/docs/2.2/programs/htpasswd.html
