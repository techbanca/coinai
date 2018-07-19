import os, sys
import json
import asyncio

current_path = os.path.realpath(__file__)
root_path = current_path.split("tools")[0]
output_path = current_path.split("tools")[0] + "/data/dbData/"
sys.path.append(root_path)

from coin_application.reports.dao import findFactorModel, findReferenceData, findRegimeModel, findRiskFactor
from coin_application.reports.models import FactorModel, ReferenceData, RegimeModel, RiskFactor
from coin_application.coins.dao import findCoinByName
from datalib.datalib import Connection
from lib import orm
from lib.config import configs
from datalib import regime_model

async def import_factor_model(tab_name):

    with open(output_path + "%s.json" % tab_name, 'r') as load_f:
        items = json.load(load_f)
        for index, obj in enumerate(items):
            factors = obj["factors"]
            factors = json.dumps(factors)
            res = await findFactorModel(obj["code"])
            if res:
                res.factors = factors
                await res.update()
            else:
                print(factors)
                factor = FactorModel(code=obj["code"],factors=factors)
                await factor.save()


async def import_reference_data(tab_name):
    with open(output_path + "%s.json" % tab_name, 'r') as load_f:
        items = json.load(load_f)
        for index, obj in enumerate(items):
            data = obj["data"]
            res = await findReferenceData(obj["code"])
            if res:
                model = await ReferenceData.find(res.id)
                model.data = data
                await model.update()
            else:
                reference = ReferenceData(code=obj["code"], data=data)
                await reference.save()


async def update_regime_model(db, model_name, factor_code, n_regimes):
    """
        Save changes to regime model and recalculate
    """
    from analytics.regime_analysis import RegimeCalculator
    factor_model = await db.get_factor_model(factor_code)
    tickers = factor_model['factors']
    tickers = json.loads(tickers.decode())
    factors = await db.get_risk_factors(tickers)
    series = [f.Performance for f in factors]
    model = regime_model.RegimeModel({'model_name': model_name,
                         'factor_code': factor_code,
                         'ngegimes': n_regimes
                         })
    
    rcalc = RegimeCalculator(series=series, n_regimes=int(n_regimes))
    rcalc.update_model(model)
    model.recalc_stats()
    dbdata = model.to_db_item()
    history = dbdata.get("history",[])
    return history


async def import_regime_model(tab_name):
    with open(output_path + "%s.json" % tab_name, 'r') as load_f:
        items = json.load(load_f)
        db = Connection.getInstance()
        for index, obj in enumerate(items):
            history = obj["history"]
            history = json.dumps(history)
            res = await findRegimeModel(obj["model_name"])
            if res:
                model = await RegimeModel.find(res.id)
                historys = await update_regime_model(db, obj["model_name"], obj["factor_code"], obj["ngegimes"])
                historys = [{"Regime":history["Regime"], "Date":float(history["Date"]) } for history in historys]
                model.factor_code = obj["factor_code"]
                model.ngegimes = int(obj["ngegimes"])
                model.history = json.dumps(historys)
                await model.update()
            else:
                factor = RegimeModel(factor_code=obj["factor_code"], model_name=obj["model_name"],
                                     ngegimes=obj["ngegimes"], history=history)
                await factor.save()


async def import_risk_factor(tab_name):
    with open(output_path + "%s.json" % tab_name, 'r') as load_f:
        items = json.load(load_f)
        for index, obj in enumerate(items):
            res = await findRiskFactor(obj["ticker"])
            coin_item = await findCoinByName(obj["name"].lower())
            if coin_item:
                coin_id = coin_item[0].get("coin_id","")
            else:
                coin_id = ""
            if res:
                model = await RiskFactor.find(res.id)
                model.name = obj["name"]
                await model.update()
            else:
                factor = RiskFactor(coin_id=coin_id, ticker=obj["ticker"], name=obj["name"])
                await factor.save()


async def main(loop):

    await orm.create_plug_pool(loop=loop, **configs.db)
    await import_factor_model("FactorModel")
    await import_reference_data("ReferenceData")
    await import_regime_model("RegimeModel")
    await import_risk_factor("RiskFactor")

if __name__ == '__main__':

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))

