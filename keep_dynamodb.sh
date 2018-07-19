#!/usr/bin/env bash

#########################################################################
# File Name: keep_dynamodb.sh
# Author: coinai
#########################################################################

basepath=$(cd `dirname $0`; pwd)

cd $basepath

num=1
iNum=1
echo $$


while(( $num < 5 ))
do
    java_cn0=`ps -ef|grep java |grep DynamoDBLocal_lib |grep 8000| grep -v grep |awk '{print $2}'`
    echo $java_cn0
    if [ "${java_cn0}" = "" ]
    then
    
        let "iNum++"
        echo $iNum
        sudo nohup java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -port 8000 -dbPath ./dbase/  &
        echo java dynamoDB_0 start ok !
    else
        echo java dynamoDB_0 running
    fi

    sleep 5
done
