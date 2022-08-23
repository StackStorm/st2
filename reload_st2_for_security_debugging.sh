#!/bin/bash
echo "Running script"
./tools/launchdev.sh stop
./tools/launchdev.sh startclean
st2 run sandbox.check-secret key=foo value=maiHuNa
