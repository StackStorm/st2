#!/bin/bash

CONFIG=$(cat <<EHD
CREATE ROLE mistral WITH CREATEDB LOGIN ENCRYPTED PASSWORD 'StackStorm';
CREATE DATABASE mistral OWNER mistral;
EHD
)

echo -e "$CONFIG" | psql -U ubuntu
