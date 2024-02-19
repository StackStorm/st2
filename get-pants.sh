#!/usr/bin/env bash
# Copyright 2023 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

set -euo pipefail

COLOR_RED="\x1b[31m"
COLOR_GREEN="\x1b[32m"
COLOR_YELLOW="\x1b[33m"
COLOR_RESET="\x1b[0m"

function log() {
  echo -e "$@" 1>&2
}

function die() {
  (($# > 0)) && log "${COLOR_RED}$*${COLOR_RESET}"
  exit 1
}

function green() {
  (($# > 0)) && log "${COLOR_GREEN}$*${COLOR_RESET}"
}

function warn() {
  (($# > 0)) && log "${COLOR_YELLOW}$*${COLOR_RESET}"
}

function check_cmd() {
  local cmd="$1"
  command -v "$cmd" > /dev/null || die "This script requires the ${cmd} binary to be on the PATH."
}

help_url="https://www.pantsbuild.org/docs/getting-help"

_GC=()

function gc() {
  if (($# > 0)); then
    check_cmd rm
    _GC+=("$@")
  else
    rm -rf "${_GC[@]}"
  fi
}

trap gc EXIT

check_cmd uname

function calculate_os() {
  local os

  os="$(uname -s)"
  if [[ "${os}" =~ [Ll]inux ]]; then
    echo linux
  elif [[ "${os}" =~ [Dd]arwin ]]; then
    echo macos
  elif [[ "${os}" =~ [Ww]in|[Mm][Ii][Nn][Gg] ]]; then
    # Powershell reports something like: Windows_NT
    # Git bash reports something like: MINGW64_NT-10.0-22621
    echo windows
  else
    die "Pants is not supported on this operating system (${os}). Please reach out to us at ${help_url} for help."
  fi
}

OS="$(calculate_os)"

check_cmd basename
if [[ "${OS}" == "windows" ]]; then
  check_cmd pwsh
else
  check_cmd curl
fi

function fetch() {
  local url="$1"
  local dest_dir="$2"

  local dest
  dest="${dest_dir}/$(basename "${url}")"

  if [[ "${OS}" == "windows" ]]; then
    pwsh -c "Invoke-WebRequest -OutFile $dest -Uri $url"
  else
    curl --proto '=https' --tlsv1.2 -sSfL -o "${dest}" "${url}"
  fi
}

if [[ "${OS}" == "macos" ]]; then
  check_cmd shasum
else
  check_cmd sha256sum
fi

function sha256() {
  if [[ "${OS}" == "macos" ]]; then
    shasum --algorithm 256 "$@"
  else
    sha256sum "$@"
  fi
}

check_cmd mktemp

function install_from_url() {
  local url="$1"
  local dest="$2"

  local workdir
  workdir="$(mktemp -d)"
  gc "${workdir}"

  fetch "${url}.sha256" "${workdir}"
  fetch "${url}" "${workdir}"
  (
    cd "${workdir}"
    sha256 -c --status ./*.sha256 ||
      die "Download from ${url} did not match the fingerprint at ${url}.sha256"
  )
  rm "${workdir}/"*.sha256
  if [[ "${OS}" == "macos" ]]; then
    mkdir -p "$(dirname "${dest}")"
    install -m 755 "${workdir}/"* "${dest}"
  else
    install -D -m 755 "${workdir}/"* "${dest}"
  fi
}

function calculate_arch() {
  local arch

  arch="$(uname -m)"
  if [[ "${arch}" =~ x86[_-]64 ]]; then
    echo x86_64
  elif [[ "${arch}" =~ arm64|aarch64 ]]; then
    echo aarch64
  else
    die "Pants is not supported for this chip architecture (${arch}). Please reach out to us at ${help_url} for help."
  fi
}

check_cmd cat

function usage() {
  cat << EOF
Usage: $0

Installs the pants launcher binary.

You only need to run this once on a machine when you do not have "pants"
available to run yet.

The pants binary takes care of managing and running the underlying
Pants version configured in "pants.toml" in the surrounding Pants-using
project.

Once installed, if you want to update your "pants" launcher binary, use
"SCIE_BOOT=update pants" to get the latest release or
"SCIE_BOOT=update pants --help" to learn more options.

-h | --help: Print this help message.

-d | --bin-dir:
  The directory to install the scie-pants binary in, "~/.local/bin" by default.

-b | --base-name:
  The name to use for the scie-pants binary, "pants" by default.

-V | --version:
  The version of the scie-pants binary to install, the latest version by default.
  The available versions can be seen at:
    https://github.com/pantsbuild/scie-pants/releases

EOF
}

bin_dir="${HOME}/.local/bin"
base_name="pants"
version="latest/download"
while (($# > 0)); do
  case "$1" in
    --help | -h)
      usage
      exit 0
      ;;
    --bin-dir | -d)
      bin_dir="$2"
      shift
      ;;
    --base-name | -b)
      base_name="$2"
      shift
      ;;
    --version | -V)
      version="download/v$2"
      shift
      ;;
    *)
      usage
      die "Unexpected argument $1\n"
      ;;
  esac
  shift
done

ARCH="$(calculate_arch)"
URL="https://github.com/pantsbuild/scie-pants/releases/${version}/scie-pants-${OS}-${ARCH}"
dest="${bin_dir}/${base_name}"

log "Downloading and installing the pants launcher ..."
install_from_url "${URL}" "${dest}"
green "Installed the pants launcher from ${URL} to ${dest}"
if ! command -v "${base_name}" > /dev/null; then
  warn "${dest} is not on the PATH."
  log "You'll either need to invoke ${dest} explicitly or else add ${bin_dir} to your shell's PATH."
fi

green "\nRunning \`pants\` in a Pants-enabled repo will use the version of Pants configured for that repo."
green "In a repo not yet Pants-enabled, it will prompt you to set up Pants for that repo."
