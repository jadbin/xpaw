#!/usr/bin/env bash

bin=$(dirname $0)
bin=$(cd "$bin"; pwd)

. "$bin"/xpaw-config.sh

echo "stop fetcher"
"$bin"/xpaw-daemon.sh stop fetcher $@
