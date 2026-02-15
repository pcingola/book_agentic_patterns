#!/bin/bash -eu
set -o pipefail

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

build-repl-image
