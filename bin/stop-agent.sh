#!/usr/bin/env bash

bin=$(dirname $0)
bin=$(cd "$bin"; pwd)

. "$bin"/xpaw-config.sh

echo "stop agent"
"$bin"/xpaw-daemon.sh stop agent $@
