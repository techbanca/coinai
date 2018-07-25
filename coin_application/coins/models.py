import time
import uuid

from lib.orm import Model, StringField, FloatField


def next_id():
	return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


class Coin(Model):

    __table__ = 'coin'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    name = StringField(ddl='varchar(50)')
    simple_name = StringField(ddl='varchar(20)')
    website_slug = StringField(ddl='varchar(50)')
    market_cap = StringField(ddl='varchar(30)')
    market_cap_btc = StringField(ddl='varchar(30)')
    price = StringField(ddl='varchar(20)')
    pre_price = StringField(ddl='varchar(20)',default="")
    supply_pvolume = StringField(ddl='varchar(20)')
    trading_24_volume = StringField(ddl='varchar(20)')
    hours_1_index = StringField(ddl='varchar(10)')
    hours_24_index = StringField(ddl='varchar(10)')
    day_7_index = StringField(ddl='varchar(10)')
    price_rate = StringField(ddl='varchar(20)')
    price_btc = StringField(ddl='varchar(20)')
    pre_price_btc = StringField(ddl='varchar(20)')
    price_btc_rate = StringField(ddl='varchar(20)')
    trading_24_btc_volume = StringField(ddl='varchar(20)')
    modify_at = FloatField(default=time.time)
    created_at = FloatField(default=time.time)

class Performance(Model):

    __table__ = 'performance'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    coin_id = StringField(ddl='varchar(50)')
    close_value = FloatField()
    net_return = FloatField()
    effective_date = FloatField(default=time.time)
    created_at = FloatField(default=time.time)


class PerformanceHour(Model):

    __table__ = 'performance_hour'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    coin_id = StringField(ddl='varchar(50)')
    close_value = FloatField()
    net_return = FloatField()
    effective_date = FloatField(default=time.time)
    created_at = FloatField(default=time.time)