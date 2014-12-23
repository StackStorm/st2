Authentication
==============

|st2| includes an auth service that is responsible for handling user authentication and generating
time limited access tokens. When authentication mode is enabled, those access tokens are used to
authenticate against the |st2| REST APIs.

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
* ``use_ssl`` - True to use SSL / TLS.
* ``cert`` - Path to the certificate file. Only used when "use_ssl" is True.
* ``key`` - Path to the private key file. Only used when "use_ssl" is True.
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

In the standalone mode, st2auth service handles the authentication itself
using a backend which is specified in the config file.

.. figure:: /_static/images/st2auth_standalone_mode.png
    :align: center

    Standalone mode

In this mode, the service should listen on https (this means setting the
``use_ssl`` configuration option) and be accessible to the st2 clients.

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
^^^^^^^^^^^^^

.. sourcecode:: bash

    st2auth --config-file /etc/stanley/st2.conf --auth-use_ssl --auth-mode=standalone \
        --auth-backend=flat_file --auth-backend_kwargs='{"file_path": "/etc/private/htpaswd"}'

Setup the service using proxy mode
----------------------------------

Install Apache and other dependencies. ::

    # Install Apache, mod_wsgi, and pwauth for mod_auth_external.
    sudo apt-get -y install apache2 libapache2-mod-wsgi libapache2-mod-authz-unixgroup pwauth

    # Supply a x509 cert or create a self-signed cert.
    sudo mkdir -p /etc/apache2/ssl
    sudo openssl req -x509 -nodes -newkey rsa:2048 -subj "/C=US/ST=California/L=Palo Alto/O=Example/CN=example.com" -keyout /etc/apache2/ssl/mycert.key -out /etc/apache2/ssl/mycert.crt

Install st2auth. The configuration file for st2auth should be located at /etc/st2/st2.conf. By default, the token expires in 24 hours.  This is configurable on the server side under token_ttl in the auth section of /etc/st2/st2.conf.  The value is in seconds.  The following example sets the TTL to 30 days. ::

    [auth]
    token_ttl = 2592000

Follow the example below and create /etc/apache2/sites-available/st2-auth.conf. The following configures st2auth to authenticate users who belong to the st2ops group, with PAM via apache.

.. literalinclude:: ../../../st2auth/conf/apache.sample.conf

Add the following line to /etc/apache2/ports.conf. ::

    Listen 9100

Enable SSL and st2-auth and restart Apache. ::

    sudo ln -s /etc/apache2/sites-available/st2-auth.conf /etc/apache2/sites-enabled/st2-auth.conf
    sudo a2enmod ssl
    sudo service apache2 restart

Testing
-------

Run the following curl commands to test. ::

    # The following will fail because SSL is required.
    curl -X POST http://myhost.example.com:9100/v1/tokens

    # The following will fail with 401 unauthorized.
    curl -X POST https://myhost.example.com:9100/v1/tokens

    # The following will succeed and return a valid token. Please note that this is executed without verifying the SSL cert.
    curl -X POST -k -u yourusername:yourpassword https://myhost.example.com:9100/v1/tokens

    # The following will verify the SSL cert.
    curl -X POST --cacert /path/to/cacert.pem -u yourusername:yourpassword https://myhost.example.com:9100/v1/tokens

Usage
-----

Once st2auth is setup, to enable st2api for authentication, change enable to True in
the auth section at :github_st2:`st2.conf <conf/st2.conf>` and restart the st2api service. ::

    [auth]
    enable = True

Once auth is enabled for st2api, API calls require token to be pass via the headers and CLI
calls requires the token to be included as CLI argument or be stored in the environment.

To acquire a new token via the CLI, run the ``st2 auth`` command.  If password is not provided,
then ``st2 auth`` will prompt for the password. If successful, a token is returned in the
response. ::

    # with password
    st2 auth yourusername -p yourpassword

    # without password
    st2 auth yourusename
    Password:

The following is a sample API call via curl using the token. ::

    curl -H "X-Auth-Token: 4d76e023841a4a91a9c66aa4541156fe" http://myhost.example.com:9101/v1/actions

The following is the equivalent for CLI. ::

    # Include token as argument.
    st2 action list -t 4d76e023841a4a91a9c66aa4541156fe

    # Put token into environment.
    export ST2_AUTH_TOKEN=4d76e023841a4a91a9c66aa4541156fe
    st2 action list

.. _htpasswd: https://httpd.apache.org/docs/2.2/programs/htpasswd.html
