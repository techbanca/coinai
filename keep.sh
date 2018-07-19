#!/usr/bin/env bash

#########################################################################
# File Name: keep.sh
# Author: coinai
#########################################################################

basepath=$(cd `dirname $0`; pwd)

cd $basepath

num=1
iNum=1
echo $$

while(( $num < 5 ))
do
    aw=`ps -ef | grep 'run_web.py 6000'| grep -v grep |awk '{print $2}'`
    echo $aw
    if [ "${aw}" = "" ]
    then
        let "iNum++"
        echo $iNum
        sudo nohup python3 run_web.py 6000 >/dev/null 2>&1  &
        echo python3 run_web.py start ok !
    else
        echo run_web.py running
    fi

    aw=`ps -ef | grep 'run_web.py 6001'| grep -v grep |awk '{print $2}'`
    echo $aw
    if [ "${aw}" = "" ] 
    then
        let "iNum++"
        echo $iNum
        sudo nohup python3 run_web.py 6001 >/dev/null 2>&1  &
        echo python3 run_web.py start ok !
    else
        echo run_web.py running
    fi


    cn=`ps -ef | grep cron_main.py | grep -v grep |awk '{print $2}'`
    echo $cn
    if [ "${cn}" = "" ]
    then
        let "iNum++"
        echo $iNum
        sudo nohup python3 tools/plugScript/cron_job/cron_main.py >/dev/null 2>&1  &
        echo cron_main.py start ok !
    else
        echo cron_main.py  running
    fi

    dr=`ps -ef | grep distribute_request_down.py | grep -v grep |awk '{print $2}'`
    echo $dr
    
    if [ "${dr}" = "" ]
    then
        let "iNum++"
        echo $iNum
        sudo nohup python3 tools/plugScript/cron_job/distribute_request_down.py >/dev/null 2>&1  &
        echo distribute_request_down.py start ok !
    else
        echo distribute_request_down.py  running
    fi

    sleep 5
done
