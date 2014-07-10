#!/usr/bin/env bash

# Drop all action-related DB collections
mongo --eval 'db.action_d_b.drop() ; db.action_type_d_b.drop() ; db.action_execution_d_b.drop() ; db.live_action_d_b.drop()' st2
