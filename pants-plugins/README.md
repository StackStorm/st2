## pants plugins

This directory contains StackStorm-specific plugins for pantsbuild.

./pants should be the primary entry point for development related tasks.
This replaces the Makefile and related scripts such that they are more discoverable.
The plugins here add custom goals or other logic into pants.

To see available goals, do "./pants help goals" and "./pants help $goal".

These StackStorm-specific plugins are probably only useful for the st2 repo.
- `schemas`

### `schemas` plugin

This plugin wires up pants to make sure `contrib/schemas/*.json` gets
regenerated whenever the source files change. Now, whenever someone runs
the `fmt` goal (eg `./pants fmt contrib/schemas::`), the schemas will
be regenerated if any of the files used to generate them have changed.
Also, running the `lint` goal will fail if the schemas need to be
regenerated.
