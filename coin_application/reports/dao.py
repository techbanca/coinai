import asyncio
import json

from decimal import Decimal
from coin_application.reports.models import FactorModel, ReferenceData, RiskFactor, RegimeModel
from lib.redis import Redis


async def getReportUpdateTime(key="update_report", item=""):
    redis_obj = Redis.getInstance()
    update_report = redis_obj.get(key)
    if update_report is None:
        return ""
    update_report = json.loads(update_report.decode()) if not isinstance(update_report, dict) else update_report
    res = update_report.get(item, {}).get("update_at","")
    return res

@asyncio.coroutine
async def findReferenceData(code):

    referenceData = await ReferenceData.findAll(where='code=?', args=[code,])
    if referenceData:
        referenceData = referenceData[0]
    return referenceData

@asyncio.coroutine
async def findRiskFactor(ticker=""):
    if ticker:
        riskFactor = await RiskFactor.findAll(where='ticker=?', args=[ticker,])
        if riskFactor:
            riskFactor = riskFactor[0]
    else:
        riskFactor = await RiskFactor.findAll()
    return riskFactor

@asyncio.coroutine
async def findFactorModel(code=None):

    if code:
        factorModel = await FactorModel.findAll(where='code=?', args=[code,])
        if factorModel:
            factorModel = factorModel[0]
        else:
            factorModels = await FactorModel.findAll()
            if factorModels:
                factorModel = factorModels[0]
        return factorModel
    else:
        factorModels = await FactorModel.findAll()
        if factorModels:
            return [{"code":factor.code, "factors":json.loads(factor.factors.decode())} for factor in factorModels]


@asyncio.coroutine
async def findRegimeModel(model_name=None):

    if model_name:
        regimeModel = await RegimeModel.findAll(where='model_name=?', args=[model_name,])
        if regimeModel:
            regimeModel = regimeModel[0]
        return regimeModel
    
    else:
        regimeModels = await RegimeModel.findAll()
        
        if regimeModels:
            return [{"factor_code":regime.factor_code, "history":[{
                        "Regime": item["Regime"],
                        "Date": Decimal(item["Date"]).quantize(Decimal('0.00'))
                      } for item in json.loads(regime.history.decode())],
                     "model_name":regime.model_name, "ngegimes":Decimal(regime.ngegimes).quantize(Decimal('0.00'))}
                    for regime in regimeModels]

