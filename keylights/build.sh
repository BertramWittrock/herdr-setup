#!/bin/sh
# Build razer-keys against librazermacos (a git submodule of this repo).
set -eu
cd "$(dirname "$0")"
[ -e librazermacos/src ] || git submodule update --init librazermacos
clang -O2 -w -framework CoreFoundation -framework IOKit \
  -I librazermacos/src/include librazermacos/src/lib/*.c razer-keys.c -o razer-keys
echo "built $(pwd)/razer-keys"
