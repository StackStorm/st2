Web UI
======

st2web is an Angular-based HTML5 web application. It allows you to control the whole process of execution, from running an action to seeing the results of the execution. It also helps you to explore workflow executions up to the results of individual tasks. All in real time.

Deployment
-----------

Production version of st2web is deployed on all-in-one installation. You can access the UI by pointing your browser to ``http://<server hostname>:8080/``. For vagrant deployment of st2express, it would be http://172.168.90.50:8080/.

.. note::

    If you want to change the default listen port you can do that by setting the ``WEBUI_PORT``
    environment variable when controlling the services using the st2ctl script.

    For example, to make the WebUI HTTP server listen on port 9999, you would run the following
    command: ``WEBUI_PORT=9999 st2ctl restart``

It can also be installed by extracting the latest tar-ball from :ops_latest:`webui` into ``/opt/stackstorm/static/webui``.

st2web is a pure html5 application and consist only of js scripts, html templates, css styles and a number of static files including custom fonts and svg images. For application to work correctly, all this files should be served to the browser.
By default they are served by python SimpleHTTPServer. For your custom deployments,
you are encouraged to host it off nginx, Apache or a similar dedicated web server to serve those static files.

Note that |st2| API endpoint should be accessible from the browser, not the web server running static content.


Configuration
-------------

For UI to work properly, both web client and |st2| server side should be configured accordingly.

On a web client side, a file ``config.js`` in a root of the project which contains the list of servers this UI can connect to. Typically `/opt/stackstorm/static/webui/config.js` The file consists of an array of objects, each have a ``name``, ``url`` and ``auth`` properties.

::

   hosts: [{
     name: 'Express Deployment',
     url: 'http://172.168.90.50:9101',
     auth: true
   },{
     name: 'Development Environment',
     url: 'http://:9101'
     auth: 'https://:9100'
   }]


Multiple servers could be configured for user to pick from. To disconnect from the current server and return to login screen, pick 'Disconnect' from the drop down at the top right corner of the UI.

On an |st2| side, `CORS <https://en.wikipedia.org/wiki/Cross-origin_resource_sharing>`__ should also be properly configured. In st2.conf, ``allow_origin`` property of the [api] section should contain the Origin header browser sends with every request. For example, if you have deployed UI on its own server and accessing it using url `http://webui.example.com:8000`, your config should look like that:

::

   [api]
   # Host and port to bind the API server.
   host = 0.0.0.0
   port = 9101
   logging = st2api/conf/logging.conf
   # List of allowed origins for CORS, use when deploying st2web client
   # The URL must match the one the browser uses to access the st2web
   allow_origin = http://webui.example.com:8000

Origin consists of scheme, hostname and port (if it isn't 80). Path (including tailing slash) should be omitted.

Please note that some of the origins is already included by default and do not require additional configuration:

* http://localhost:3000 - development version of `gulp` running locally
* http://localhost:9101,http://127.0.0.1:9101 - st2api pecan deployment (st2_deploy default)
* `api_url` from [auth] section of st2.conf

Also, please note that although this is not recommended and will undermine your security, you can allow every web UI deployment to connect to your server by setting ``allow_origin = *``.

Authentication
--------------

To configure st2web to support authentication, edit ``config.js`` and add ``auth:true`` to every server that supports authentication. To enable authentication on a server side, please refer to :doc:`../authentication`.


