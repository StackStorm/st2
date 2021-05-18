#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from st2common.runners.base_action import Action


class EECC(Action):
    def run(self, message, cmd):
        secretParam = "MMNNPP"        
        return {"secretParam": secretParam}
