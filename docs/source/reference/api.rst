REST API Reference
===================

Work in progress...

Meantime, using ``--debug`` key may help: used on any CLI command, it prints `curl` and outputs raw response:

::

    $ st2 --debug action list
    ...
    # -------- begin 140419231392336 request ----------
    curl -X GET -H  'Connection: keep-alive' -H  'User-Agent: python-requests/2.8.1' -H  'Accept-Encoding: gzip, deflat
    e' -H  'Accept: */*' -H  'X-Auth-Token: cf7a543c015d4a76ae0a7ca02073d69b' https://172.31.0.104:9101/actions
    # -------- begin 140419231392336 response ----------
    [{"description": "Run ad-hoc ansible command (module)", "runner_type":
    ...

.. todo: publish complete REST API