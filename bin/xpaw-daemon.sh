#!/usr/bin/env bash

if [ $# -le 1 ]; then
    exit 1
fi

bin=$(dirname $0)
bin=$(cd "$bin"; pwd)

. "$bin"/xpaw-config.sh

cmd=$1
shift
name=$1
shift

if [ ! -d "$XPAW_LOG_DIR" ]; then
    mkdir -p "$XPAW_LOG_DIR"
fi
if [ ! -d "$XPAW_PID_DIR" ]; then
    mkdir -p "$XPAW_PID_DIR"
fi

log="$XPAW_LOG_DIR"/xpaw-"$XPAW_ID_STRING"-"$name".log
pid="$XPAW_PID_DIR"/xpaw-"$XPAW_ID_STRING"-"$name".pid
stop_timeout=5

case $cmd in
    start)
        nohup "$PYTHON" -m xpaw "$cmd" "$name" $@ > "$log" 2>&1 < /dev/null &
        echo $! > "$pid"
        sleep 3
        if ! ps -p $! > /dev/null; then
            echo "fail to start $name"
            exit 1
        fi
        ;;
    stop)
        if [ -f "$pid" ]; then
            target_pid=$(cat "$pid")
            if kill -0 $target_pid > /dev/null 2>&1; then
                echo "kill $target_pid"
                kill $target_pid
                sleep $stop_timeout
                if kill -0 $target_pid > /dev/null 2>&1; then
                    echo "$name did not stop gracefully after $stop_timeout seconds: killing with kill -9"
                    kill -9 $target_pid
                fi
            else
                echo "no $name to stop"
            fi
            rm -f "$pid"
        else
            echo "no $name to stop"
        fi
        ;;
    *)
        exit 1
        ;;
esac
