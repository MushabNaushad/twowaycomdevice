#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="$DIR/../blocks/gr-transport/build/lib:$LD_LIBRARY_PATH"
exec /usr/bin/python3 -u "$@"
