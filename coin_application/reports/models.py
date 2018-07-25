import time
import uuid

from lib.orm import Model, StringField, FloatField


def next_id():
	return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


class FactorModel(Model):

    __table__ = 'factor_model'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    code = StringField(ddl='varchar(20)')
    factors = StringField(ddl='blob', default="")
    created_at = FloatField(default=time.time)


class ReferenceData(Model):

    __table__ = 'reference_data'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    code = StringField(ddl='varchar(20)')
    data = StringField(ddl='blob', default="")
    created_at = FloatField(default=time.time)


class RiskFactor(Model):

    __table__ = 'risk_factor'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    coin_id = StringField(ddl='varchar(50)')
    ticker = StringField(ddl='varchar(20)')
    name = StringField(ddl='varchar(20)')
    created_at = FloatField(default=time.time)


class RegimeModel(Model):
    """
    {
        "factorCode": "BANCA",
        "ngegimes": 5.0,
        "modelName": "BIG date",
        "history": [
          {
            "Regime": "Regime 3",
            "Date": 1493510400.0
          }
        ]
    }
    """
    __table__ = 'regime_model'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    factor_code = StringField(ddl='varchar(20)')
    model_name = StringField(ddl='varchar(20)')
    ngegimes = FloatField(default=1.0)
	
    history = StringField(ddl='blob', default="")
    created_at = FloatField(default=time.time)
