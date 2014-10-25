Authentication Service
======================

###Deploy to Apache

Install Apache and other dependencies.

    # Install Apache, mod_wsgi, and pwauth for mod_auth_external.
    sudo apt-get -y install apache2 libapache2-mod-wsgi libapache2-mod-authz-unixgroup pwauth
    
    # Supply a x509 cert or create a self-signed cert.
    sudo mkdir -p /etc/apache2/ssl
    sudo openssl req -x509 -nodes -newkey rsa:2048 -subj "/C=US/ST=California/L=Palo Alto/O=Example/CN=example.com" -keyout /etc/apache2/ssl/mycert.key -out /etc/apache2/ssl/mycert.crt

Install st2auth.  The configuration file for st2auth should be located at /etc/st2/st2.conf.

Follow the example below and create /etc/apache2/sites-available/st2-auth.conf. The following configures st2auth to authenticate users who belong to the st2ops group, with PAM via apache. 

    <VirtualHost *:9100>
    
        ServerName myhost.example.com:9100
    
        WSGIScriptAlias / /path/to/st2auth/st2auth/wsgi.py
        WSGIDaemonProcess st2auth user=myuser group=mygroup processes=2 threads=25 python-path=/path/to/st2auth:/path/to/st2common:/path/to/virtualenv/local/lib/python2.7/site-packages
        WSGIProcessGroup st2auth
    
        SSLEngine on
        SSLCertificateFile /etc/apache2/ssl/mycert.crt
        SSLCertificateKeyFile /etc/apache2/ssl/mycert.key
    
        AddExternalAuth pwauth /usr/sbin/pwauth
        SetExternalAuthMethod pwauth pipe
    
        <Directory /path/to/st2auth/st2auth>
            <Files wsgi.py>
                Order deny,allow
                Allow from all
            </Files>
            AuthType Basic
            AuthName "Restricted"
            AuthBasicProvider external
            AuthExternal pwauth
            require unix-group st2ops
        </Directory>
    
    </VirtualHost>

Add the following line to /etc/apache2/ports.conf.

    Listen 9100

Enable SSL and st2-auth and restart Apache.

    sudo ln -s /etc/apache2/sites-available/st2-auth.conf /etc/apache2/sites-enabled/st2-auth.conf
    sudo a2enmod ssl
    sudo service apache2 restart

###Testing
    
Run the following curl commands to test.

    # The following will fail because SSL is required.
    curl -X POST http://myhost.example.com:9100/tokens

    # The following will fail with 401 unauthorized.
    curl -X POST https://myhost.example.com:9100/tokens

    # The following will succeed and return a valid token. Please note that this is executed without verifying the SSL cert.
    curl -X POST -k -u yourusername:yourpassword https://myhost.example.com:9100/tokens

    # The following will verify the SSL cert.
    curl -X POST --cacert /path/to/cacert.pem -u yourusername:yourpassword https://myhost.example.com:9100/tokens

###Usage

Once st2auth is setup, to enable st2api for authentication, change enable to True in the auth section at st2.conf and restart the st2api service.

    [auth]
    enable = True

Once auth is enabled for st2api, API calls require token to be pass via the headers and CLI calls requires the token to be included as CLI argument or be stored in the environment.

To acquire a new token via the CLI, run the st2 auth command.  If password is not provided, then st2 auth will prompt for the password.  If successful, a token is returned in the response. 

    # with password
    st2 auth yourusername -p yourpassword
    
    # without password
    st2 auth yourusename
    Password:

The following is a sample API call via curl using the token.

    curl -H "X-Auth-Token: 4d76e023841a4a91a9c66aa4541156fe" http://myhost.example.com:9101/actions

The following is the equivalent for CLI.

    # Include token as argument.
    st2 action list -t 4d76e023841a4a91a9c66aa4541156fe
    
    # Put token into environment.
    export ST2_AUTH_TOKEN=4d76e023841a4a91a9c66aa4541156fe
    st2 action list

By default, the token expires in 24 hours.  This is configurable on the server side under token_ttl in the auth section.  The value is in seconds.  The following example sets the TTL to 30 days.

    [auth]
    token_ttl = 2592000

###Mistral Integration

Communications from mistral to st2 uses the REST API. Therefore, a token is required in the headers of the REST calls. Currently, token for integration with external systems have to be generated manually.

    # Connect to the database.
    from oslo.config import cfg
    from st2auth import config
    cfg.CONF(args=['--config-file', '/etc/st2/st2.conf'])
    from st2common.models import db
    db.db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port)

    # Create user entry and generate a token.
    import uuid
    from datetime import datetime
    from st2common.models.db.access import *
    from st2common.persistence.access import *
    User.add_or_update(UserDB(name='mistral'))
    Token.add_or_update(TokenDB(user='mistral', token=uuid.uuid4().hex, expiry=datetime(2015, 1, 1)))

Once a token has been generated, put the token under auth_token at the st2 section in the mistral.conf file and then restart the mistral service.

    [st2]
    auth_token = a42ddd39632e4661b46e08bdd791c0a5
