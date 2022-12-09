## pants plugins

This directory contains StackStorm-specific plugins for pantsbuild.

./pants should be the primary entry point for development related tasks.
This replaces the Makefile and related scripts such that they are more discoverable.
The plugins here add custom goals or other logic into pants.

To see available goals, do "./pants help goals" and "./pants help $goal".
