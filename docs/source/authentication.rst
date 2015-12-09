Authentication
==============

|st2| includes an auth service that is responsible for handling user authentication and generating
time limited access tokens. When authentication mode is enabled (default for all-in-one installer
and package based installations), those access tokens are used to authenticate against the |st2|
REST APIs.

.. figure:: /_static/images/st2auth_standalone_mode.png
    :align: center

Configuring the Service
-----------------------

By default, the |st2| configuration file is located at /etc/st2/st2.conf. The available settings
listed below are configured under the ``auth`` section in the configuration file. The service can
be configured with different backends (i.e. PAM, LDAP, etc.) to handle the authentication. If
backend is not specified, a htpasswd compatible flat file authentication backend is used. It is
recommended that the service be configured to listen on https (use_ssl option) and be accessible
to the st2 clients.

* ``host`` - Hostname for the service to listen on.
* ``port`` - Port for the service to listen on.
* ``use_ssl`` - Set to True to enable SSL / TLS mode.
* ``cert`` - Path to the SSL certificate file. Only used when "use_ssl" is set to True.
* ``key`` - Path to the SSL private key file. Only used when "use_ssl" is set to True.
* ``mode`` - Mode to use (``proxy`` or ``standalone``). Default is ``standalone``.
* ``backend`` - Authentication backend to use in standalone mode (i.e. pam, flat_file). Please
  review the supported list of authentication backends below.
* ``backend_kwargs`` - JSON serialized arguments which are passed to the authentication backend in
  standalone mode.
* ``token_ttl`` - The value in seconds when the token expires. By default, the token expires in 24
  hours.
* ``api_url`` - Authentication service also acts as a service catalog. It returns a URL to the API
  endpoint on successful authentication. This information is used by clients such as command line
  tool and web UI. The setting needs to contain a public base URL to the API endpoint (excluding
  the API version). Example: ``https://myhost.example.com/api/``
* ``enable`` - Authentication is not enabled for the |st2| API until this is set to True. If
  running |st2| on multiple servers, please ensure that this is set to True on all |st2|
  configuration files.
* ``debug`` - Specify to enable debug mode.

After the configuration change, restart all st2 components.

.. sourcecode:: bash

    st2ctl restart

Auth Backends
-------------
The service can be configured with different backends (i.e. PAM, LDAP, etc.) to handle the
authentication. If backend is not specified, a htpasswd compatible flat file authentication
backend is used. The all-in-one installer and packages download and configure PAM by default. To
use a different backend, select and install the appropriate python package from the |st2|
`community repos <https://github.com/StackStorm?utf8=✓&query=st2-auth>`_ and configure st2auth
accordingly. For example, to install the package for the PAM backend manually, run the following
command on the same server where st2auth is running.

.. sourcecode:: bash

    pip install git+https://github.com/StackStorm/st2-auth-backend-pam.git@master#egg=st2_auth_backend_pam

After the backend is installed, configure the backend at /etc/st2/st2.conf, and restart |st2|.
Specific configuration details for the backend can be found in the README at the corresponding
repo. The following is a sample auth section in the config file for the PAM backend.

.. sourcecode:: ini

    [auth]
    mode = standalone
    backend = pam
    enable = True
    use_ssl = True
    cert = /path/to/ssl/cert/file
    key = /path/to/ssl/key/file
    logging = /etc/st2/st2auth.logging.conf
    api_url = https://myhost.examples.com/api/
    debug = False

The following is a list of auth backends for the community edition to help get things started.

* `PAM <https://github.com/StackStorm/st2-auth-backend-pam>`_
* `Flat File <https://github.com/StackStorm/st2-auth-backend-flat-file>`_
* `OpenStack Keystone <https://github.com/StackStorm/st2-auth-backend-keystone>`_

LDAP (Enterprise Edition)
-------------------------
StackStorm developed auth backends such as LDAP are only available in the enterprise edition. For
more information on the enterprise edition, please visit https://stackstorm.com/product/#enterprise.
The auth backends included with the enterprise edition are developed, tested, maintained, and
supported by the StackStorm team.

LDAP
^^^^
The LDAP backend authenticates user against an LDAP server. The following is a list of
configuration options for the backend.

+----------+----------+---------+------------------------------------------------------------+
| option   | required | default | description                                                |
+==========+==========+=========+============================================================+
| users_ou | yes      |         | OU of the user accounts                                    |
+----------+----------+---------+------------------------------------------------------------+
| host     | yes      |         | Hostname of the LDAP server                                |
+----------+----------+---------+------------------------------------------------------------+
| port     | yes      |         | Port of the LDAP server                                    |
+----------+----------+---------+------------------------------------------------------------+
| use_ssl  | no       | false   | Use LDAPS to connect                                       |
+----------+----------+---------+------------------------------------------------------------+
| use_tls  | no       | false   | Start TLS on LDAP to connect                               |
+----------+----------+---------+------------------------------------------------------------+
| cacert   | no       | None    | Path to the CA cert used to validate certificate           |
+----------+----------+---------+------------------------------------------------------------+
| id_attr  | no       | uid     | Field name of the user ID attribute                        |
+----------+----------+---------+------------------------------------------------------------+
| scope    | no       | subtree | Search scope (base, onelevel, or subtree)                  |
+----------+----------+---------+------------------------------------------------------------+

The following is a sample auth section for the LDAP backend in the st2 config file.

.. sourcecode:: ini

    [auth]
    mode = standalone
    backend = ldap
    backend_kwargs = {"users_ou": "ou=users,dc=example,dc=com", "host": "identity.example.com", "port": 636, "use_ssl": true, "cacert": "/path/to/cacert.pem"}
    enable = True
    use_ssl = True
    cert = /path/to/mycert.crt
    key = /path/to/mycert.key
    logging = /path/to/st2auth.logging.conf
    api_url = https://myhost.example.com/api/
    debug = False

Running the Service
-------------------
The all-in-one installer sets up st2auth to run as a service. The service is setup to run under
nginx with uwsgi. Alternate configuration with gunicorn or apache is also possible using wsgi.py
under st2auth but we leave as an exercise for the reader.

The service can be started with one of the options below.

.. sourcecode:: bash

    # Individually
    service st2auth start

    # Individually via st2ctl
    st2ctl start st2auth

    # Collectively with other st2 components
    st2ctl start

    # Using the launcher for debugging purposes
    /usr/bin/st2auth --config-file /etc/st2/st2.conf

Testing
-------

Run the following curl commands to test.

.. sourcecode:: bash

    # If use_ssl is set to True, the following will fail because SSL is required.
    curl -X POST http://myhost.example.com/auth/v1/tokens

    # The following will fail with 401 unauthorized. Please note that this is executed with "-k" to skip SSL cert verification.
    curl -X POST -k https://myhost.example.com/auth/v1/tokens

    # The following will succeed and return a valid token. Please note that this is executed with "-k" to skip SSL cert verification.
    curl -X POST -k -u yourusername:yourpassword https://myhost.example.com/auth/v1/tokens

    # The following will verify the SSL cert, succeed, and return a valid token.
    curl -X POST --cacert /path/to/cacert.pem -u yourusername:yourpassword https://myhost.example.com/auth/v1/tokens

.. note:: Until version 1.2 of StackStorm, auth APIs were served from its own port. If your version is 1.1.1 or below, replace '/api' with ':9100'.

.. _authentication-usage:

Usage
-----

Once st2auth is setup, API calls require token to be passed via the headers and the CLI calls
require the token to be included as a CLI argument or be provided as an environment variable.

.. include:: auth_usage.rst

.. _authentication-apikeys:

API Keys
--------

|st2| also supports API keys which differ from tokens in the sense that they do not expire and are
therefore suited to be use with integrations like webhooks etc.

All API key management is currently available via the |st2| CLI.

To create an API key -

.. sourcecode:: bash

   st2 apikey create -k -m '{"used_by": "my integration"}'
   <API_KEY_VALUE>

.. note::

    For security purposes the <API_KEY_VALUE> is only show at create time. |st2| itself does not
    store this API Key value in its database, only a one-way hash is stored. It is not possible to
    retrieve an API Key after creation. If the API Key is lost or not recorded at the time of
    creation it is best to delete the API Key and create a new one.

The optional ``-m`` attribute allows metadata to be associated with the created key. It is good
practice to assign a meaningful value like the external service which uses this key to authenticate
with |st2|.

The CLI for API keys also support `get`, `list`, `delete`, `enable` and `disable` commands.

If an API Key is disabled it will disallow access until that API key is enabled again. This is a
good way to temporarily revoke access of an external service to |st2|.

API Key Usage
^^^^^^^^^^^^^

API keys are designed for API access. As of now they cannot be used via clients like the UI and CLI.

The following are sample API calls via curl using API Keys. ::

    curl -H "St2-Api-Key: <API-KEY-VALUE>" https://myhost.example.com/api/v1/actions

    curl https://myhost.example.com/api/v1/actions?st2-api-key=<API-KEY-VALUE>


.. _htpasswd: https://httpd.apache.org/docs/2.2/programs/htpasswd.html
