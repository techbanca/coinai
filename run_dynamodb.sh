#!/usr/bin/env bash

#########################################################################
# File Name: run_dynamodb.sh
# Author: coinai
#########################################################################

basepath=$(cd `dirname $0`; pwd)

cd $basepath


if [ "$1" = "start" ]; then
    set -x
    echo "It is starting the dynamoDB local server!"

    java_cn0=`ps -ef|grep java |grep DynamoDBLocal_lib |grep 8000| grep -v grep |awk '{print $2}'`
    echo $java_cn0
    if [ "${java_cn0}" = "" ]
    then
        sudo nohup java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -port 8000 -dbPath ./dbase/  &
        echo java dynamoDB_0 start ok !
    else
        echo "java dynamoDB_0 running"
    fi

    kp=`ps -ef | grep keep_dynamodb.sh | grep -v grep |awk '{print $2}'`
    echo $kp
    if [ "${kp}" = "" ]
    then
        sudo nohup sh keep_dynamodb.sh >/dev/null 2>&1 &
    else
        echo "keep_dynamodb.sh  running"
    fi


elif [ "$1" = "stop" ]; then

    echo "It is stopping the dynamoDB local server!"
    ps -ef|grep -E 'DynamoDBLocal_lib|keep_dynamodb.sh' | grep -v grep | awk '{print $2}' | xargs kill -9

fi
