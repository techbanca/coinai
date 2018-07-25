import time
import uuid

from lib.orm import Model, StringField, FloatField, IntegerField


def next_id():
	return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


class Portfolio(Model):

    __table__ = 'portfolio'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = IntegerField()
    name = StringField(ddl='varchar(30)', default="")
    read_num = IntegerField(default=0)
    init_assets = IntegerField(default=1000000)
    allocations = StringField(ddl='blob', default="")
    allocations_history = StringField(ddl='blob', default="")
    entire_history = FloatField(default=0.0)
    pre_roi = FloatField(default=1000000)
    pre_date = StringField(ddl='varchar(20)', default="")
    hour_24_history = FloatField(default=0.0)
    max_history = FloatField(default=0.0)
    day_7_history = FloatField(default=0.0)
	
    day_30_history = FloatField(default=0.0)
    day_60_history = StringField(ddl='varchar(20)', default="0.0%")
    day_90_history = StringField(ddl='varchar(20)', default="0.0%")
    day_182_history = StringField(ddl='varchar(20)', default="0.0%")
    day_365_history = StringField(ddl='varchar(20)', default="0.0%")
    max_drawdown = StringField(ddl='varchar(20)', default="")
    day_7_drawdown = StringField(ddl='varchar(20)', default="")
    day_7_volatility = StringField(ddl='varchar(20)', default="")
    volatility = StringField(ddl='varchar(20)', default="")
    data_num = IntegerField(default=0)
    modify_at = FloatField(default=time.time)
    created_at = FloatField(default=time.time)


class FolioPerformance(Model):

    __table__ = 'folio_performance'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    folio_id = StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    performance_data = StringField(ddl='blob', default="")
    state = IntegerField(default=0)
    modify_at = FloatField(default=time.time)
    created_at = FloatField(default=time.time)
