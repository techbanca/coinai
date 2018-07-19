#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

    Represents User data from DynamoDB

    Developed by Coin-AI, 2017-2018
    Contact: banca
"""

class User:
    def __init__(self, item):
        
        self.userid = item['UserID']
        self.email = item['EMail']
        self.firstName = item['First Name']
        self.lastName = item['Last Name']
        self.userType = item['usertype']
        if 'Company' in item:
            self.company = item['Company']
        self.password = item['Password']
        self.authenticated = False
        self.CompanyID = item['CompanyID']
        
    def authenticate(self, pwd):
       
        self.authenticated = self.password == pwd
        
    def is_authenticated(self):
        return self.authenticated
        
    def is_active(self):
        return self.authenticated
        
    def get_id(self):
        return self.userid
    
    
