#!/usr/bin/env bash

mkdir /mnt/ramdisk
mount -t tmpfs -o size=1024m tmpfs /mnt/ramdisk
