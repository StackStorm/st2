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

    # Include the token as command line argument.
    st2 action list -t 4d76e023841a4a91a9c66aa4541156fe

    # Or set the token as an environment variable.
    export ST2_AUTH_TOKEN=4d76e023841a4a91a9c66aa4541156fe
    st2 action list

Note that there can be use cases when you want the TTL to be different from default.
You can specify a TTL (in seconds) when you request a token. To get a token that is valid
for 10 minutes, use the following:

::

    # with TTL and password
    st2 auth yourusername -p yourpassword -t 600
