#!/usr/bin/env python
# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from __future__ import absolute_import

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import argparse
import os
import pprint

from st2common.runners.parallel_ssh import ParallelSSHClient


def main(user, pkey, password, hosts_str, cmd, file_path, dir_path, delete_dir):
    hosts = hosts_str.split(",")
    client = ParallelSSHClient(
        user=user, pkey_file=pkey, password=password, hosts=hosts
    )
    pp = pprint.PrettyPrinter(indent=4)

    if file_path:
        if not os.path.exists(file_path):
            raise Exception("File not found.")
        results = client.put(file_path, "/home/lakshmi/test_file", mode="0660")
        pp.pprint("Copy results: \n%s" % results)
        results = client.run("ls -rlth")
        pp.pprint("ls results: \n%s" % results)

    if dir_path:
        if not os.path.exists(dir_path):
            raise Exception("File not found.")
        results = client.put(dir_path, "/home/lakshmi/", mode="0660")
        pp.pprint("Copy results: \n%s" % results)
        results = client.run("ls -rlth")
        pp.pprint("ls results: \n%s" % results)

    if cmd:
        results = client.run(cmd)
        pp.pprint("cmd results: \n%s" % results)

    if delete_dir:
        results = client.delete_dir(delete_dir, force=True)
        pp.pprint("Delete results: \n%s" % results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parallel SSH tester.")
    parser.add_argument("--hosts", required=True, help="List of hosts to connect to")
    parser.add_argument("--private-key", required=False, help="Private key to use.")
    parser.add_argument("--password", required=False, help="Password.")
    parser.add_argument("--user", required=True, help="SSH user name.")
    parser.add_argument("--cmd", required=False, help="Command to run on host.")
    parser.add_argument(
        "--file", required=False, help="Path of file to copy to remote host."
    )
    parser.add_argument(
        "--dir", required=False, help="Path of dir to copy to remote host."
    )
    parser.add_argument(
        "--delete-dir", required=False, help="Path of dir to delete on remote host."
    )
    args = parser.parse_args()

    main(
        user=args.user,
        pkey=args.private_key,
        password=args.password,
        hosts_str=args.hosts,
        cmd=args.cmd,
        file_path=args.file,
        dir_path=args.dir,
        delete_dir=args.delete_dir,
    )
