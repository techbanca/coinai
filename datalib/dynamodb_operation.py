#!/usr/bin/python
# -*- encoding: utf-8 -*-

import boto3
import json
import sys
from datetime import datetime, timedelta
from conf import dynamodb_config


class dynamodb_operation():
    def __init__(self, path):
        conf = dynamodb_config.dynamoDB
        self.client = boto3.client('dynamodb', region_name=conf['region_name'],
                                   aws_access_key_id=conf['aws_access_key_id'],
                                   aws_secret_access_key=conf['aws_secret_access_key'])
        self.conf_path = path
        self.items = ['TableName', 'AttributeDefinitions', 'KeySchema', 'LocalSecondaryIndexes',
                      'GlobalSecondaryIndexes', 'ProvisionedThroughput', 'StreamSpecification']

    def load_json(self, path):
        try:
            with open(path) as json_file:
                data = json.load(json_file)
        except Exception as e:
            print('ERROR: no such file like ' + path)
            exit(-1)
        else:
            return data

    def create_table(self, tablename, keySchema, attributeDefinitions, provisionedThroughput):
        table = self.client.create_table(
            TableName=tablename,
            KeySchema=keySchema,
            AttributeDefinitions=attributeDefinitions,
            ProvisionedThroughput=provisionedThroughput
        )

        # Wait until the table exists.
        self.client.get_waiter('table_exists').wait(TableName=tablename)

        response = self.client.describe_table(TableName=tablename)
        print(response)

    def get_item_desc(self, item, content):
        try:
            result = content[item]
        except Exception as e:
            result = []
        return result

    def create_table_from_desc(self, path):
        table_desc = self.load_json(path)
        provisionedThroughput = {
            'ReadCapacityUnits': 6,
            'WriteCapacityUnits': 6
        }
        tableName = self.get_item_desc('TableName', table_desc)
        attributeDefinitions = self.get_item_desc('AttributeDefinitions', table_desc)
        keySchema = self.get_item_desc('KeySchema', table_desc)
        localSecondaryIndexes = self.get_item_desc('LocalSecondaryIndexes', table_desc)
        globalSecondaryIndexes = self.get_item_desc('GlobalSecondaryIndexes', table_desc)
        streamSpecification = self.get_item_desc('StreamSpecification', table_desc)

        if len(globalSecondaryIndexes):
            for item in globalSecondaryIndexes:
                item['ProvisionedThroughput'] = provisionedThroughput

        try:
            if len(localSecondaryIndexes):
                if len(globalSecondaryIndexes):
                    table = self.client.create_table(
                        TableName=tableName,
                        KeySchema=keySchema,
                        AttributeDefinitions=attributeDefinitions,
                        ProvisionedThroughput=provisionedThroughput,
                        LocalSecondaryIndexes=localSecondaryIndexes,
                        GlobalSecondaryIndexes=globalSecondaryIndexes
                    )
                else:
                    table = self.client.create_table(
                        TableName=tableName,
                        KeySchema=keySchema,
                        AttributeDefinitions=attributeDefinitions,
                        ProvisionedThroughput=provisionedThroughput,
                        LocalSecondaryIndexes=localSecondaryIndexes
                    )
            else:
                if len(globalSecondaryIndexes):
                    table = self.client.create_table(
                        TableName=tableName,
                        KeySchema=keySchema,
                        AttributeDefinitions=attributeDefinitions,
                        ProvisionedThroughput=provisionedThroughput,
                        GlobalSecondaryIndexes=globalSecondaryIndexes
                    )
                else:
                    table = self.client.create_table(
                        TableName=tableName,
                        KeySchema=keySchema,
                        AttributeDefinitions=attributeDefinitions,
                        ProvisionedThroughput=provisionedThroughput
                    )

        except Exception as e:
            print('ERROR: error desc like file: ' + path + '\tmsg: ' + str(e))
            exit(-1)

        else:
            # Wait until the table exists.
            self.client.get_waiter('table_exists').wait(TableName=tableName)

            response = self.client.describe_table(TableName=tableName)
            print(response)

    def get_table_desc_only(self, table):
        try:
            response = self.client.describe_table(TableName=table)
        except Exception as e:
            print('ERROR: no such table like ' + table)
            exit(-1)
        else:
            return response["Table"]

    def check_table_is_exist(self, table):
        try:
            response = self.client.describe_table(TableName=table)
        except Exception as e:
            return 0
        else:
            return 1

    def get_SecondaryIndexes_desc(self, content):
        result = []
        for sub_item in content:
            sub_content = {}
            sub_content['IndexName'] = sub_item['IndexName']
            sub_content['KeySchema'] = sub_item['KeySchema']
            sub_content['Projection'] = sub_item['Projection']
            result.append(sub_content)
        return result

    def get_table_desc_for_create_table(self, table):
        response = self.get_table_desc_only(table)
        result = {}
        for item in self.items:
            try:
                content = response[item]
            except Exception as e:
                continue
            else:
                if item == 'TableName':
                    if content != table:
                        print('ERROR: dynamoDB get table desc error')
                        exit(-1)
                    result[item] = content

                elif item == 'LocalSecondaryIndexes' or item == 'GlobalSecondaryIndexes':
                    result[item] = self.get_SecondaryIndexes_desc(content)
                    continue

                elif item == 'ProvisionedThroughput':
                    continue

                else:
                    result[item] = content
                    continue

        return json.dumps(result)

    def get_table_size(self, table):
        response = self.get_table_desc_only(table)
        stastic = {}
        stastic['TableSizeBytes'] = response['TableSizeBytes']
        stastic['ItemCount'] = response['ItemCount']
        return stastic

    def list_all_table(self):
        page = 1
        LastEvaluationTableName = ""
        while True:
            if page == 1:
                response = self.client.list_tables()
            else:
                response = self.client.list_tables(
                    ExclusiveStartTableName=LastEvaluationTableName
                )
            TableNames = response['TableNames']
            for table in TableNames:
                print(table)
            if response.has_key('LastEvaluatedTableName'):
                LastEvaluationTableName = response["LastEvaluatedTableName"]
            else:
                break
            page += 1

    def get_stastic(self, dimension):
        conf = self.load_json(self.conf_path)
        cw = boto3.client('cloudwatch', region_name=conf['region_name'], aws_access_key_id=conf['aws_access_key_id'],
                          aws_secret_access_key=conf['aws_secret_access_key'])

        stastic = {}
        stastic['Write'] = 0
        stastic['Read'] = 0

        # write
        table_stastic = cw.get_metric_statistics(Namespace='AWS/DynamoDB', MetricName='ConsumedWriteCapacityUnits',
                                                 Dimensions=dimension,
                                                 StartTime=datetime.utcnow() - timedelta(days=9),
                                                 EndTime=datetime.utcnow(),
                                                 Period=900, Statistics=['Sum', 'Maximum'], Unit='Count')['Datapoints']

        if len(table_stastic) > 1:
            for item in table_stastic:
                stastic['Write'] += int(item['Sum'])

        # read
        table_stastic = cw.get_metric_statistics(Namespace='AWS/DynamoDB', MetricName='ConsumedReadCapacityUnits',
                                                 Dimensions=dimension,
                                                 StartTime=datetime.utcnow() - timedelta(days=9),
                                                 EndTime=datetime.utcnow(),
                                                 Period=900, Statistics=['Sum', 'Maximum'], Unit='Count')['Datapoints']

        if len(table_stastic) > 1:
            for item in table_stastic:
                stastic['Read'] += int(item['Sum'])

        return stastic

    def get_table_use(self, table_name):
        dimension = [{'Name': 'TableName', 'Value': table_name}]
        stastic = self.get_stastic(dimension)
        table = self.get_table_desc_only(table_name)
        for index in table.get('GlobalSecondaryIndexes', []):
            if index['IndexStatus'] != 'ACTIVE':
                return
            dimension = [{'Name': 'TableName', 'Value': table_name},
                         {'Name': 'GlobalSecondaryIndexName', 'Value': index['IndexName']}]
            tmp = self.get_stastic(dimension)
            stastic['Write'] += tmp['Write']
            stastic['Read'] += tmp['Read']

        return stastic

    def check_table_is_use(self, stastic):
        read = stastic['Write']
        write = stastic['Read']
        if read == 0 and write == 0:
            return False
        else:
            return True

    def delete_table(self, table):
        try:
            self.client.delete_table(
                TableName=table
            )
        except Exception as e:
            print('ERROR: delete table ' + table + ' fail. msg: ' + str(e))
        else:
            print('delete table ' + table + ' succ')

    def list_dynamodb_conf(self):
        conf = self.load_json(self.conf_path)
        print( 'region_name=' + '"' + conf['region_name'] + '"')
        print('aws_access_key_id=' + '"' + conf['aws_access_key_id'] + '"')
        print('aws_secret_access_key=' + '"' + conf['aws_secret_access_key'] + '"')

    def put_item(self, tableName, item):
        try:
            self.client.put_item(
                TableName=tableName,
                Item=item
            )
        except Exception as e:
            print('ERROR: put item fail. msg: ' + str(e))
            exit(-1)
        else:
            return

    def put_items(self, tableName, item_path):
        for item in open(item_path):
            self.put_item(tableName, eval(item))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("cmd                                  args")
        print("list_all_table")
        print("list_dynamodb_conf")
        print("get_table_desc_for_create_table      table")
        print("get_table_desc_only                  table")
        print("get_table_size                       table")
        print("create_table_from_desc               table_desc_file")
        print("check_table_is_exist                 table")
        print("get_table_use                        table")
        print("delete_table                         table               password")
        print("put_item                             table               item(json)")
        print("put_items                            table               item_file_path")
        exit(-1)

    db = dynamodb_operation('../conf/dynamoDB.conf')

    cmd = str(sys.argv[1])
    if len(sys.argv) == 2:
        if cmd == 'list_all_table':
            db.list_all_table()
        if cmd == 'list_dynamodb_conf':
            db.list_dynamodb_conf()

    if len(sys.argv) == 3:
        if cmd == 'get_table_desc_for_create_table':
            table = str(sys.argv[2])
            print(db.get_table_desc_for_create_table(table))

        if cmd == 'get_table_desc_only':
            table = str(sys.argv[2])
            print(db.get_table_desc_only(table))

        if cmd == 'check_table_is_exist':
            table = str(sys.argv[2])
            print(db.check_table_is_exist(table))

        if cmd == 'get_table_size':
            table = str(sys.argv[2])
            print(db.get_table_size(table))

        if cmd == 'create_table_from_desc':
            desc_file_path = str(sys.argv[2])
            db.create_table_from_desc(desc_file_path)

        if cmd == 'get_table_use':
            table = str(sys.argv[2])
            stastic = db.get_table_use(table)
            print(stastic)
            db.check_table_is_use(stastic)

    if len(sys.argv) == 4:
        if cmd == 'delete_table':
            table = str(sys.argv[2])
            password = str(sys.argv[3])
            if password == 'password':
                db.delete_table(table)
            else:
                print('ERROR: password error!')
                exit(-1)

        if cmd == 'put_item':
            table = str(sys.argv[2])
            tmp = str(sys.argv[3])
            item = eval(tmp)
            db.put_item(table, item)

        if cmd == 'put_items':
            table = str(sys.argv[2])
            item_file_path = str(sys.argv[3])
            db.put_items(table, item_file_path)
