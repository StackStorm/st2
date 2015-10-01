SSH troubleshooting
===================

Since v0.13, Paramiko runner is the default SSH runner in |st2|. Most of this
documentation assumes you are using paramiko runner. Wherever behavior is different from
fabric runner, it will be called out.

|st2| remote actions use the ``system_user`` and ``ssh_key_file`` in configuration file (
usually /etc/st2/st2.conf) as authentication credentials to remote boxes. This is to lock
down so all remote actions are run as defined user (default is ``stanley``). The ``
ssh_key_file`` is private key file (RSA/DSA) for ``system_user``. You can change the
username and key file by setting appropriate values in the config file. In case of key
compromises, revoking public key for ``system_user`` from target boxes will revoke access
for |st2| from target boxes. We also recommend adding ``system_user`` to a linux group and
control permissions on target boxes as an additional security measure.

To validate remote actions are working correctly, you can use the following command.

::

    # Default run
    $st2 run core.remote cmd=whoami hosts=localhost
    id: 55dff0bd32ed356c736318b0
    status: succeeded
    result:
    {
        "localhost": {
            "succeeded": true,
            "failed": false,
            "return_code": 0,
            "stderr": "",
            "stdout": "stanley"
        }
    }

If you don't have the right SSH key file, you will see an error and action will fail.

::

    st2 run core.remote cmd=whoami hosts=localhost
    .
    id: 55dff9e132ed350bae2b5217
    status: failed
    result:
    {
        "traceback": "  File "/mnt/src/storm/st2/st2actions/st2actions/container/base.py", line 99, in _do_run
        runner.pre_run()
      File "/mnt/src/storm/st2/st2actions/st2actions/runners/ssh/paramiko_ssh_runner.py", line 138, in pre_run
        connect=True
      File "/mnt/src/storm/st2/st2actions/st2actions/runners/ssh/parallel_ssh.py", line 55, in __init__
        connect_results = self.connect(raise_on_any_error=raise_on_any_error)
      File "/mnt/src/storm/st2/st2actions/st2actions/runners/ssh/parallel_ssh.py", line 85, in connect
        raise NoHostsConnectedToException(msg)
    ",
        "error": "Unable to connect to any one of the hosts: [u'localhost'].

     connect_errors={
      "localhost": {
        "failed": true,
        "traceback": "  File \"/mnt/src/storm/st2/st2actions/st2actions/runners/ssh/parallel_ssh.py\", line 239, in _connect\n    client.connect()\n  File \"/mnt/src/storm/st2/st2actions/st2actions/runners/ssh/paramiko_ssh.py\", line 134, in connect\n    self.client.connect(**conninfo)\n  File \"/mnt/src/storm/st2/virtualenv/local/lib/python2.7/site-packages/paramiko/client.py\", line 307, in connect\n    look_for_keys, gss_auth, gss_kex, gss_deleg_creds, gss_host)\n  File \"/mnt/src/storm/st2/virtualenv/local/lib/python2.7/site-packages/paramiko/client.py\", line 519, in _auth\n    raise saved_exception\n",
        "return_code": 255,
        "succeeded": false,
        "error": "Cannot connect to host. not a valid EC private key file"
      }
    }"

All automations (rules that kickoff remote actions or scripts) by default will use this
username and private_key combination.

.. note::

    If you are not using default SSH port 22, you can specify port as part of host string in hosts list like hosts=localhost:55,st2build001:56. Fabric doesn't let you do this.
    To get around the problem, set ``use_ssh_config`` to True in config file and setup ~/.ssh/config on |st2| action runner boxes appropriately.

We do not recommend running automations as arbitrary user + private_key combination. This
would require you to setup private_key for the users on stackstorm action runner boxes and
the public keys of the users in target boxes. This increases the surface area for risk and
is highly discouraged.

Said that, if you have st2client installed and want to run one off commands on remote
boxes as a different user, we have a way.

::

    $st2 run core.remote cmd=whoami hosts=localhost username=test_user private_key="`cat /home/vagrant/.ssh/id_rsa`"
    .
    id: 55dff0de32ed356c736318b9
    status: succeeded
    result:
    {
        "localhost": {
            "succeeded": true,
            "failed": false,
            "return_code": 0,
            "stderr": "",
            "stdout": "test_user"
        }
    }

In the above case, test_user's public key was added in target box (localhost). If you look
carefully, we are sending the contents of the private_key file as command argument (note
that the output of cat command is quoted). If you have SSL turned on for |st2| API, the
contents of your SSH private key are sent encrypted over the wire. If you are not using
SSL, you'll expose your private key to eavesdroppers. Therefore we highly recommend using
SSL for |st2| APIs in general and particularly for this case. With paramiko, this
private_key contents are held only in memory and is not logged or persisted anywhere.
However, due to implementation limitations of fabric, we create a temporary file with
contents of private_key and delete the file after command is complete (either succeeded or
failed). This is unsafe and we recommend moving away from Fabric runner.

If you are running remote actions as ``sudo``, pseudo tty is enabled by default. This means
that ``stdout`` and ``stderr`` streams get combined into one and reported as ``stdout``. This
is true for both fabric and paramiko ssh runner.
