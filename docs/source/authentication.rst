Authentication
==============

|st2| includes an auth service that is responsible for handling user authentication and generating
time limited access tokens. When authentication mode is enabled (authentication mode is enabled by
default for package based installations), those access tokens are used to authenticate against the
|st2| REST APIs.

The auth service can run in either proxy or standalone modes as described below.

Proxy mode
----------

In proxy mode which is configured by default, authentication is handled upstream from the st2auth service.

.. figure:: /_static/images/st2auth_proxy_mode.png
    :align: center

    Proxy mode

The service upstream is responsible for performing the authentication. If the
provided credentials are correct, the service needs to populate ``REMOTE_USER``
environment variable and proxy the request to the st2auth service. The
st2auth service then generates a new access token and returns it back to the
client.

An example of services which can perform authentication upstream include
Apache httpd, Nginx and load balancer.

If you are using Apache httpd, this means you can utilize one of the many
`existing authentication modules <http://httpd.apache.org/docs/2.2/howto/auth.html>`_
(e.g. basic auth, PAM module, kerberos module, etc.).

When you are running authentication service in the proxy mode, you need to make
sure the service is only accessible to the upstream service which is responsible
for handling authentication.

This usually means running the upstream service on the same host as the
st2auth service and configuring st2auth to only listen on ``localhost``. As an
alternative, you can run upstream service on a different host inside the same
private network and configure the st2auth service to listen on an internal IP
and configure the firewall on that host so only the upstream service can access
it.

Standalone mode
---------------

In the standalone mode, st2auth service handles the authentication itself using a backend which is specified in the config file.

.. figure:: /_static/images/st2auth_standalone_mode.png
    :align: center

    Standalone mode

In this mode, the service should listen on https (this means setting the
``use_ssl`` configuration option) and be accessible to the st2 clients.

|st2| ships with a flat file and a mongodb authentication backends that can be configured in standalone mode. Please refer to the configuration section below on how to configure these backends.

Configuring the service
-----------------------

By default, the |st2| configuration file is located at /etc/st2/st2.conf. The available settings listed below are configured under the ``auth`` section in the configuration file.

* ``host`` - Hostname for the service to listen on.
* ``port`` - Port for the service to listen on.
* ``use_ssl`` - Specify to enable SSL / TLS mode.
* ``cert`` - Path to the SSL certificate file. Only used when "use_ssl" is specified.
* ``key`` - Path to the SSL private key file. Only used when "use_ssl" is specified.
* ``mode`` - Mode to use (``proxy`` or ``standalone``). Defaults to ``proxy``.
* ``backend`` - Authentication backend to use in standalone mode (mongodb,flat_file).
* ``backend_kwargs`` - JSON serialized arguments which are passed to the authentication backend in standalone mode.
* ``token_ttl`` - The value in seconds when the token expires. By default, the token expires in 24 hours.
* ``api_url`` - Authentication service also acts as a service catalog. It returns a URL to the API endpoint on successful authentication. This information is used by clients such as command line tool and web UI. The setting needs to contain a public base URL to the API endpoint (excluding the API version). Example: http://myhost.example.com:9101/
* ``enable`` - Authentication is not enabled for the |st2| API until this is set to True. If running |st2| on multiple servers, please ensure that this is set to True on all |st2| configuration files.
* ``debug`` - Specify to enable debug mode.

Setup proxy mode
----------------------------------

The following example hosts the |st2| auth service in Apache and configures Apache to authenticates users.

Example ``auth`` section in the |st2| configuration file. ::

    [auth]
    mode = proxy
    enable = True
    debug = False
    logging = /etc/st2/st2auth.logging.conf
    api_url = http://myhost.example.com:9101/

Install Apache and other dependencies. ::

    # Install Apache, mod_wsgi, and pwauth for mod_auth_external.
    sudo apt-get -y install apache2 libapache2-mod-wsgi libapache2-mod-authz-unixgroup pwauth

    # Supply a x509 cert or create a self-signed cert.
    sudo mkdir -p /etc/apache2/ssl
    sudo openssl req -x509 -nodes -newkey rsa:2048 -subj "/C=US/ST=California/L=Palo Alto/O=Example/CN=example.com" -keyout /etc/apache2/ssl/mycert.key -out /etc/apache2/ssl/mycert.crt

Follow the example below and create /etc/apache2/sites-available/st2-auth.conf. The following configures st2auth to authenticate users who belong to the st2ops group, with PAM via apache.

.. literalinclude:: ../../st2auth/conf/apache.sample.conf

The path to the st2auth module is different depending on how |st2| is installed.

+----------------+--------------------------------------------------------+
| install method | st2auth path                                           |
+================+========================================================+
| source         | /path/to/st2/git/clone/st2auth/st2auth                 |
+----------------+--------------------------------------------------------+
| st2express     | /usr/lib/python2.7/dist-packages/st2auth               |
+----------------+--------------------------------------------------------+
| debian package | /usr/lib/python2.7/dist-packages/st2auth               |
+----------------+--------------------------------------------------------+
| fedora package | /usr/lib/python2.7/site-packages/st2auth               |
+----------------+--------------------------------------------------------+

Add the following line to /etc/apache2/ports.conf. ::

    Listen 9100

Enable SSL and st2-auth and restart Apache. ::

    sudo ln -s /etc/apache2/sites-available/st2-auth.conf /etc/apache2/sites-enabled/st2-auth.conf
    sudo a2enmod ssl
    sudo service apache2 restart

Setup standalone mode
------------------------------------

The following is a list of authentication backends that is available to configure in standalone mode.

Flat file backend
~~~~~~~~~~~~~~~~~

Flat file backend supports reading credentials from an Apache HTTPd htpasswd
formatted file. To manage this file you can use `htpasswd`_ utility which comes
with a standard Apache httpd distribution or by installing apache2-utils.

    **Backend configuration options:**

    * ``file_path`` - Path to the file containing credentials.

Example htpasswd command to generate a password file with a user entry. ::

    htpasswd -cm /path/to/.htpasswd stark

Example ``auth`` section in the |st2| configuration file. ::

    [auth]
    mode = standalone
    backend = flat_file
    backend_kwargs = {"file_path": "/path/to/.htpasswd"}
    enable = True
    debug = False
    use_ssl = True
    cert = /path/to/mycert.crt
    key = /path/to/mycert.key
    logging = /path/to/st2auth.logging.conf
    api_url = http://myhost.example.com:9101/

MongoDB backend
~~~~~~~~~~~~~~~

MongoDB backend supports reading credentials from a MongoDB collection called ``users``. This
backend is supported only if debug in the |st2| configuration file is set to True. Currently,
the MongoDB collection and the user entries will have to be generated manually. Entries in this
``users`` collection need to have the following attributes:

    * ``username`` - Username
    * ``salt`` - Password salt
    * ``password`` - SHA256 hash for the salt+password - SHA256(<salt><password>)

    **Backend configuration options:**

    * ``db_host`` - MongoDB server host.
    * ``db_port`` - MongoDB server port.
    * ``db_name`` - Name of the database to use.

Example ``auth`` section in the |st2| configuration file. ::

    [auth]
    mode = standalone
    backend = mongodb
    backend_kwargs = {"db_host": "127.0.0.1", "db_port": 27017, "db_name": "st2auth"}
    enable = True
    debug = True
    use_ssl = True
    cert = /path/to/mycert.crt
    key = /path/to/mycert.key
    logging = /path/to/st2auth.logging.conf
    api_url = http://myhost.example.com:9101/

LDAP backend
~~~~~~~~~~~~~~~~
Backend which reads authentication information from a ldap server.
The backend tries to bind the ldap user with given username and password.
If the bind was successful, it tries to find the user in the given group.
If the user is in the group, he will be authenticated.

    **Backend configuration options:**

    * ``ldap_server`` - URL of the LDAP Server.
    * ``base_dn`` - Base DN on the LDAP Server.
    * ``group_dn`` - Group DN on the LDAP Server which contains the user as member.
    * ``scope`` - Scope search parameter. Can be base, onelevel or subtree (default: subtree)
    * ``use_tls`` - Boolean parameter to set if tls is required

Example ``auth`` section in the |st2| configuration file. ::

    [auth]
    mode = standalone
    backend = ldap_backend
    backend_kwargs = {"ldap_server": "ldap://ds.example.com", "base_dn": "ou=people,dc=example,dc=com", "group_dn": "cn=sysadmins,ou=groups,dc=example,dc=com", "scope": "", "use_tls": "True"}
    enable = True
    debug = False
    use_ssl = True
    cert = /path/to/mycert.crt
    key = /path/to/mycert.key
    logging = /etc/st2auth/logging.conf
    api_url = http://myhost.example.com:9101/
    host = 0.0.0.0
    port = 9100



Keystone backend
~~~~~~~~~~~~~~~~

Keystone backend supports authenticating against a Keystone auth server.

    **Backend configuration options:**

    * ``keystone_url`` - Keystone server url, port included (e.x. "http://keystone.com:5000").
    * ``keystone_version`` - Keystone api version to use. Defaults to 2.

Example ``auth`` section in the |st2| configuration file. ::

    [auth]
    mode = standalone
    backend = keystone
    backend_kwargs = {"keystone_url": "http://keystone.com:5000", "keystone_version": 2}
    enable = True
    debug = True
    use_ssl = True
    cert = /path/to/mycert.crt
    key = /path/to/mycert.key
    logging = /path/to/st2auth.logging.conf
    api_url = http://myhost.example.com:9101/

After the configuration change, restart all st2 components. ::

    st2ctl restart

Testing
-------

Run the following curl commands to test. ::

    # The following will fail because SSL is required.
    curl -X POST http://myhost.example.com:9100/tokens

    # The following will fail with 401 unauthorized. Please note that this is executed with "-k" to skip SSL cert verification.
    curl -X POST -k https://myhost.example.com:9100/tokens

    # The following will succeed and return a valid token. Please note that this is executed with "-k" to skip SSL cert verification.
    curl -X POST -k -u yourusername:yourpassword https://myhost.example.com:9100/tokens

    # The following will verify the SSL cert, succeed, and return a valid token.
    curl -X POST --cacert /path/to/cacert.pem -u yourusername:yourpassword https://myhost.example.com:9100/tokens

.. _authentication-usage:

Usage
-----

Once st2auth is setup, API calls require token to be passed via the headers and the CLI calls
require the token to be included as a CLI argument or be provided as an environment variable.

.. include:: auth_usage.rst

.. _htpasswd: https://httpd.apache.org/docs/2.2/programs/htpasswd.html
