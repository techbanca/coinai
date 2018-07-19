#!/usr/bin/env bash

#########################################################################
# File Name: run_server.sh
# Author: coinai
#########################################################################

sudo mkdir -p /var/log/coin_ai

basepath=$(cd `dirname $0`; pwd)

cd $basepath

if [ "$1" = "start" ]; then
    set -x 
    echo "It is starting all the task server!"

    aw=`ps -ef | grep 'run_web.py 6000'| grep -v grep |awk '{print $2}'`
    echo $aw
    if [ "${aw}" = "" ]
    then
        sudo nohup python3 run_web.py 6000 >/dev/null 2>&1 &
    else
        echo run_web.py running
    fi

    aw=`ps -ef | grep 'run_web.py 6001'| grep -v grep |awk '{print $2}'`
    echo $aw
    if [ "${aw}" = "" ]
    then
        sudo nohup python3 run_web.py 6001 >/dev/null 2>&1 &
    else
        echo run_web.py running
    fi


    cn=`ps -ef | grep cron_main.py | grep -v grep |awk '{print $2}'`
    echo $cn
    if [ "${cn}" = "" ]
    then
        sudo nohup python3 tools/plugScript/cron_job/cron_main.py >/dev/null 2>&1 &
    else
        echo cron_main.py  running
    fi

    dr=`ps -ef | grep distribute_request_down.py | grep -v grep |awk '{print $2}'`
    echo $dr
    if [ "${dr}" = "" ]
    
    then
        sudo nohup python3 tools/plugScript/cron_job/distribute_request_down.py >/dev/null 2>&1 &
        sudo nohup python3 tools/plugScript/cron_job/distribute_request_down.py >/dev/null 2>&1 &
    else
        echo distribute_request_down.py  running
    fi

    kp=`ps -ef | grep keep.sh | grep -v grep |awk '{print $2}'`
    echo $kp
    if [ "${kp}" = "" ]
    then
        sudo nohup sh keep.sh >/dev/null 2>&1 &
    else
        echo keep.sh  running
    fi

elif [ "$1" = "stop" ]; then
    echo "It is stopping all the task server!"
    ps -ef|grep -E 'run_web.py 6000|run_web.py 6001|keep.sh' | grep -v grep | awk '{print $2}' | xargs kill -9

elif [ "$1" = "stopAll" ]; then
    echo "It is stopping all the task server!"
    ps -ef|grep -E 'run_web.py|keep.sh|cron_main.py|distribute_request_down.py' | grep -v grep | awk '{print $2}' | xargs kill -9

else
    echo "Usage: bash  run_server.sh  [ start |stop ]"

fi

