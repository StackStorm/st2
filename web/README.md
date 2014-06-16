Stanley UI
==========

In general, you should be able to `make all` from the root of Stanley project to get it all going.

If it's for some reason not working as it should, here is a full sequence of steps to make it work:

First of all, you need to make sure you have latest stable `node` and `npm` packages installed.

    $ node -v
    v0.10.28

    $ npm -v
    1.3.6

then you need to globally install `bower` and `gulp`

    $ npm install -g bower
    $ npm install -g gulp

then you need to change your working directory to *stanley/web* and install the requirements

    $ cd stanley/web
    $ npm install
    $ bower install

and finally run build system to fetch the font, compile css and so on

    $ gulp

At that point you should be able to point your browser to [host]:3000 and see the the page.

It should be noted that `make all` is calling `gulp build` which neither starts a server to serve the page nor mocks the API. If you intend not only to build this thing, but also preview it, you would have to call `gulp mockapi serve` or `gulp serve` or set up your own web server. Calling just `gulp` both mocks and serves so it's better suited for development, but will not pass CI.
