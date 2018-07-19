# coinai
coinai is a set of seed applications based on AI for digital currency quantitative analysis, medium-term forecast, and asset allocation for the secondary market of the BANCA community.

Clients can use CoinAI to conduct in-depth analysis of digital tokens and compare the investment value and risk of different currencies.
They can also obtain the prediction for the future trend of tokens based on artificial intelligence and big data smart beta market timing models. According to your own risk assessment, you are one click away from building the optimum portfolio.

Based on the dynamic management of the optimized portfolio on token fund and outstanding old backtesting performance, the return is far higher than that of Bitcoin, while the risk is far below.


Install the project of coinai running environment:



1) install gcc , gcc-c++ ...

$ yum install gcc zlib zlib-devel python-devel libffi-devel openssl openssl-devel


$ yum install gcc-c++


2) install python3.6

$ mkdir -p /usr/local/python3


$ tar -zxvf Python-3.6.1.tgz


$ cd Python-3.6.1


$ ./configure --prefix=/usr/local/python3 --enable-optimizations


$ make


$ make install


$ ln -s /usr/local/python3/bin/python3 /usr/bin/python3


$ vim ~/.bash_profile


#.bash_profile

#Get the aliases and functions

if [ -f ~/.bashrc ]; then
. ~/.bashrc
fi

#User specific environment and startup programs

PATH=$PATH:$HOME/bin:/usr/local/python3/bin
export PATH

$ source ~/.bash_profile


3) set  pip3

$ ln -s /usr/local/python3/bin/pip3 /usr/bin/pip3

4) install  boto3

$ pip3 install boto3

$ sudo pip3 install awscli

$ aws help

$ aws configure

    AWS Access Key ID [None]: AIOSFODMPLE
    AWS Secret Access Key [None]: wJalrXUtMI/KDENG/bPxREXAMPKEY
    Default region name [None]: us-west-2
    Default output format [None]: ENTER

$ ls ~/.aws

$ ln -s /usr/local/python3/bin/aws /usr/bin/aws


5) init dynamodb

$ sudo aws dynamodb create-table --cli-input-json file://./ReportCache.json --endpoint-url http://localhost:8000

$ sudo nohup java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -port 8000 -dbPath ./dbase/ &


6) init mysql:

$ sudo mysql -hlocalhost -uroot -p"******" < schema.sql


7) install other Modular:

$ sudo pip3 install -r requirements.txt


8) run the web:

$ sudo sh run_server.sh start

or

$ sudo sh run_server.sh stop





