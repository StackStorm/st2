#! /usr/bin/python

import subprocess
import random
import re
from st2actions.runners.pythonrunner import Action


class DigAction(Action):

    def run(self, rand, count, nameserver, hostname, queryopts):
        opt_list = []
        output = []

        cmd_args = ['dig']
        if nameserver:
            nameserver = '@' + nameserver
            cmd_args.append(nameserver)

        if re.search(',', queryopts):
            opt_list = queryopts.split(',')
        else:
            opt_list.append(queryopts)
        for k, v in enumerate(opt_list):
            cmd_args.append('+' + v)

        cmd_args.append(hostname)
        result_list = filter(None, subprocess.Popen(cmd_args,
                                                    stderr=subprocess.PIPE,
                                                    stdout=subprocess.PIPE)
                                             .communicate()[0]
                                             .split('\n'))
        if int(count) > len(result_list) or count <= 0:
            count = len(result_list)

        output = result_list[0:count]
        if rand is True:
            random.shuffle(output)
        return output
