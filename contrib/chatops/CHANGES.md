# Changelog

## [1.1.0] - 2020-10-02
### Added
- added `notify-errbot` rule to better support err-stackstorm users.

## [1.0.2] - 2019-11-22
### Added
- `route` to `post_result` parameters to be propagated through to `post_message`.

## [1.0.1] - 2018-11-06
### Added
- `note` to `post_result` output to inform if the action-alias execution result was enabled or disabled.

### Changed
- Ported `post_result` action-chain to orquesta for conditional branching.

## 0.3.0

- Introduce the following new actions:
  * ``chatops.match``
  * ``chatops.match_and_execute``
  * ``chatops.run``
