Web UI
======

st2web is an Angular-based web application. It allows you to control the whole process of execution, from running an action to seeing the results of the execution. It also helps you to explore workflow executions up to the results of individual tasks. All in real time.

Express installation
--------------------

Production version of st2web is pre-installed on st2express and any other st2_deploy installation. You can access the UI by accessing **/webui** endpoint of st2api server. For vagrant deployment of st2express, it would be http://172.168.90.50:9101/webui.

It can also be installed by extracting the latest tar-ball from `https://ops.stackstorm.net/releases/st2/<st2 version>/webui/` into `/opt/stackstorm/static/webui`.

This type of installation has no additional requirements.

Development
-----------

With production version it is almost impossible to make any changes in code, besides configuration. In case any changes are needed, development version has to be installed.

First of all, you need to make sure you have latest stable node and npm packages installed.

::

   $ node -v
   v0.10.32

   $ npm -v
   1.4.9

then you need to globally install bower and gulp.

::

   $ npm install -g bower
   $ npm install -g gulp


Clone the latest version of st2web repository

::

   $ git clone https://github.com/StackStorm/st2web.git
   $ cd st2web

then you need to install the requirements

::

   $ npm install
   $ bower install

and finally run build system to lint js files, compile css and watch for changes

::

   $ gulp

At that point you should be able to point your browser to http://localhost:3000/ and see the the page. Every change in code would be automatically recompiled.

Gulp has several additional options:

* `gulp build` - just lint and compile everything
* `gulp test` - build the project and then run e2e tests
* `gulp serve` - build the project and start serving it at 3000 port
* `gulp production` - build production version of the project

The production version of the code is located in the `build/` folder. It consists of compiled and minified versions of JS and CSS files, doesn't have any additional dependencies and can be deployed to any server that can serve static files. The version produced by `gulp production` is an exact copy of the data used in Express installation and can be deployed the same way.

Configuration
-------------

For UI to work properly, both client and server side should be configured properly.

On a UI side, there is a file `config.js` in a root of the project which contains the list of servers this UI can connect to. The file consists of an array of objects, each have a `name`, `url` and `auth` properties.

::

   hosts: [{
     name: 'Express Deployment',
     url: 'http://172.168.90.50:9101',
     auth: true
   },{
     name: 'Development Environment',
     url: 'http://172.168.50.50:9101'
   }]


Multiple servers could be configured for user to pick from. To disconnect from the current server and return to login screen, pick 'Disconnect' from the drop down at the top right corner of the UI.

On an ST2 side, `CORS <https://en.wikipedia.org/wiki/Cross-origin_resource_sharing>`__ should also be properly configured. In st2.conf, `allow_origin` property of the [api] section should contain the Origin header browser sends with every request. For example, if you have deployed UI on its own server and accessing it using url `http://webui.example.com:8000`, your config should look like that:

::

   [api]
   # Host and port to bind the API server.
   host = 0.0.0.0
   port = 9101
   logging = st2api/conf/logging.conf
   # List of allowed origins for CORS, use when deploying st2web client
   # The URL must match the one the browser uses to access the st2web
   allow_origin = http://st2web.example.com:3000

Origin consists of scheme, hostname and port (if it isn't 80). Path (including tailing slash) should be omitted.

Please note that some of the origins is already included by default and do not require additional configuration:

* http://localhost:3000 - development version of `gulp` running locally
* http://localhost:9101,http://127.0.0.1:9101 - st2api pecan deployment (st2_deploy default)
* `api_url` from [auth] section of st2.conf

Also, please note that although this is not recommended and will undermine your security, you can allow every web UI deployment to connect to your server by setting `allow_origin = *`.

Authentication
--------------

To configure st2web to support authentication, edit `config.js` and add `auth:true` to every server that supports authentication. To enable authentication on a server side, please refer to :doc:`/install/deploy`.

For now, UI assumes st2auth is running on the same server with st2api on the port 9100. This is known issue and will be fixed in the next release.

It is highly recommended to ony use authentication alongside with SSL encryption (for st2web, st2api and st2auth) to mitigate possible MITM attacks and avoid sending passwords and auth tokens in plain text.