## pants plugins

This directory contains StackStorm-specific plugins for pantsbuild.

`pants` should be the primary entry point for development related tasks.
This replaces the Makefile and related scripts such that they are more discoverable.
The plugins here add custom goals or other logic into pants.

To see available goals, do "pants help goals" and "pants help $goal".

These plugins might be useful outside of the StackStorm project:
- `uses_services`

These StackStorm-specific plugins might be useful in other StackStorm-related repos.
- `pack_metadata`

These StackStorm-specific plugins are probably only useful for the st2 repo.
- `api_spec`
- `macros.py` (not a plugin - see pants.toml `[GLOBAL].build_file_prelude_globs`)
- `release`
- `sample_conf`
- `schemas`

### `api_spec` plugin

This plugin wires up pants to make sure `st2common/st2common/openapi.yaml`
gets regenerated if needed. Now, whenever someone runs the `fmt` goal
(eg `pants fmt st2common/st2common/openapi.yaml`), the api spec will
be regenerated if any of the files used to generate it has changed.
Also, running the `lint` goal will fail if the schemas need to be
regenerated.

This plugin also wires up pants so that the `lint` goal runs additional
api spec validation on `st2common/st2common/openapi.yaml` with something
like `pants lint st2common/st2common/openapi.yaml`.

### `macros.py` macros

[Macros](https://www.pantsbuild.org/docs/macros) are a pants feature
that can reduce "boilerplate"/duplication in BUILD files. The functions
defined in `macros.py` are available in all the BUILD files, and using
them looks just like using the normal BUILD targets.

For documentation about our macros, please refer to the function docstrings
in the `macros.py` file.

### `pack_metadata` plugin

This plugin adds two new targets to pants:
- `pack_metadata`
- `pack_metadata_in_git_submodule`

These targets include all StackStorm pack metadata files in a pack.
Pack metadata includes top-level files (`pack.yaml`, `<pack>.yaml.example`,
`config.schema.yaml`, and `icon.png`) and metadata (`*.yaml`, `*.yml`)
for actions, action-aliases, policies, rules, and sensors.

This plugin also wires up the `tailor` goal, so that it will add a
`pack_metadata(name="metadata")` target wherever it finds a `pack.yaml` file.

One of the packs in this repo is in a git submodule to test our handling
of git submodules (`st2tests/st2tests/fixtures/packs/test_content_version`).
If it is not checked out, then some of the tests will fail.
If it is not checked out, `pack_metadata_in_git_submodule` handles providing
a helpful, instructive error message as early as possible.

### `release` plugin

This plugin implements the [`SetupKwargs`](https://www.pantsbuild.org/docs/plugins-setup-py)
plugin hook that pants uses when it auto-generates a `setup.py` file whenever
it builds a `python_distribution()` (ie a wheel or an sdist). This makes it
easy to centralize all of the common bits of metadata that need to go in all
the wheels (like `author="StackStorm"` or our `project_urls`).

### `sample_conf` plugin

This plugin wires up pants to make sure `conf/st2.conf.sample` gets
regenerated whenever the source files change. Now, whenever someone runs
the `fmt` goal (eg `pants fmt conf/st2.conf.sample`), the sample will
be regenerated if any of the files used to generate it have changed.
Also, running the `lint` goal will fail if the sample needs to be
regenerated.

### `schemas` plugin

This plugin wires up pants to make sure `contrib/schemas/*.json` gets
regenerated whenever the source files change. Now, whenever someone runs
the `fmt` goal (eg `pants fmt contrib/schemas::`), the schemas will
be regenerated if any of the files used to generate them have changed.
Also, running the `lint` goal will fail if the schemas need to be
regenerated.

### `uses_services` plugin

This plugin validates that services are running if required. For example, some tests
need mongo, so this plugin can ensure mongo is running. If it is not running, then
an error with instructions on how to run it are given to the user.

`uses_services` has some StackStorm-specific assumptions in it, but it might be
generalizable. There are several other StackStorm-specific plugins, but some of
them are only useful in the st2 repo.
