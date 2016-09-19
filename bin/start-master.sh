#!/usr/bin/env bash

bin=$(dirname $0)
bin=$(cd "$bin"; pwd)

. "$bin"/xpaw-config.sh

config="$XPAW_CONF_DIR"/master.yaml
data_dir="$XPAW_DATA_DIR"
logger="$XPAW_CONF_DIR"/logger.yaml

echo "start master"
"$bin"/xpaw-daemon.sh start master --config "$config" --data-dir "$data_dir" --logger "$logger" $@
