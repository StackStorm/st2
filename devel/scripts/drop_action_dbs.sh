#!/usr/bin/env bash

# Drop all action-related DB collections
mongo --eval 'db.action_d_b.drop() ; db.action_type_d_b.drop() ; db.action_execution_d_b.drop() ; db.live_action_d_b.drop()' st2

# Note: The actionrunner controller must be restarted after using this script.
#       (Restarting the actionrunner controller has the side-effect of re-populating the actiontypes collection.)
