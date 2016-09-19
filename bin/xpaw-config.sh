#!/usr/bin/env bash

bin=$(dirname $0)
bin=$(cd "$bin"; pwd)

export XPAW_HOME=${XPAW_HOME:-$(cd "$bin"/../; pwd)}
export XPAW_CONF_DIR=${XPAW_CONF_DIR:-"$XPAW_HOME"/conf}

if [ -f "$XPAW_CONF_DIR"/xpaw-env.sh ]; then
    . "$XPAW_CONF_DIR"/xpaw-env.sh
fi

export XPAW_DATA_DIR=${XPAW_DATA_DIR:-"$XPAW_HOME"/.data}
export XPAW_LOG_DIR=${XPAW_LOG_DIR:-"$XPAW_HOME"/.log}
export XPAW_PID_DIR=${XPAW_PID_DIR:-"$XPAW_HOME"/.pid}
export XPAW_ID_STRING=${XPAW_ID_STRING:-$USER}
