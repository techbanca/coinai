
import time
import uuid

from lib.orm import Model, StringField, FloatField, IntegerField


def next_id():
	return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


class User(Model):

    __table__ = 'user'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = IntegerField()
    name = StringField(ddl='varchar(30)')
    nickname = StringField(ddl='varchar(30)', default="")
    head_image_url = StringField(ddl='varchar(30)', default="")
    option_one = StringField(ddl='varchar(20)', default="")
    option_two = StringField(ddl='varchar(20)', default="")
    option_three = StringField(ddl='varchar(20)', default="")
    score = IntegerField(default=0)
    ratio = FloatField(default=0.0)
    state = IntegerField(default=0)
    created_at = FloatField(default=time.time)