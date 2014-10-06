#!/usr/bin/env python

import shlex
import sys
import subprocess
import lib.datatransformer as transformer


def main(args):
    command_list = shlex.split('apt-cache policy ' + ' '.join(args[1:]))
    process = subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    command_stdout, command_stderr = process.communicate()
    command_exitcode = process.returncode
    try:
        payload = transformer.to_json(command_stdout, command_stderr, command_exitcode)
    except Exception as e:
        sys.stderr.write('JSON conversion failed. %s' % str(e))
        sys.exit(1)

    sys.stdout.write(payload)

if __name__ == '__main__':
    main(sys.argv)
