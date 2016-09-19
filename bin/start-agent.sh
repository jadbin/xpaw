#!/usr/bin/env bash

bin=$(dirname $0)
bin=$(cd "$bin"; pwd)

. "$bin"/xpaw-config.sh

config="$XPAW_CONF_DIR"/agent.yaml
data_dir="$XPAW_DATA_DIR"
logger="$XPAW_CONF_DIR"/logger.yaml

echo "start agent"
"$bin"/xpaw-daemon.sh start agent --config "$config" --data-dir "$data_dir" --logger "$logger" $@
