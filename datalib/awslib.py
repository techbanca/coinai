import json
from os import path
import boto
from boto.s3.key import Key

class AwsHelper:
    def __init__(self,bucket_name):
        self.bucket_name = bucket_name
        self.conn = boto.connect_s3()
        self.bucket = self.conn.get_bucket(self.bucket_name)

        
    def upload(self,key,text):

        k = Key(self.bucket)
        k.key = key
        return k.set_contents_from_string(text)

