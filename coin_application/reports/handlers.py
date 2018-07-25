import json
import statsmodels.api as sm

from datetime import datetime
from analytics.basicstats import BasicStats
from analytics.helper import StatsHelper
from analytics.monte_carlo.monte_carlo import ESGSimulator, MonteCarlo
from analytics.optimizer import Optimizer
from analytics.peer_analysis import PeerAnalysis
from analytics.portfolio_attribution import PortfolioAttribution
from analytics.regression_analysis import RegressionAnalysis
from analytics.time_series import get_frequency, freq_map, prev_eom, align_series
from coin_application.portfolios import dao as folios_dao
from coin_application.reports import dao as report_dao
from coin_application.reports.coinReport import StyleAnalysis, f2d, BasicReport, get_benchmarks, BenchmarkAnalysis, \
    get_histogram, portfolio_ratios
from datalib.datalib import Connection
from lib.baseweb import get
from lib.utils import toList, toDecimal, toPreTimestamp, _
from settings import windows, regime_val


@get('/coinai/get/reports/portfolio/ratios/{folio_id}',auth=True)
async def portfolio_ratios_report(folio_id, request):
    """

    :param folio_id:
    :param request:
    :return: {"error":0,
                "data":{"ResultsAll":[['Number of Periods', '290'], ['Frequency', 'D']],
                 "RollResults":[[2, [['Number of Periods', '20'], ['Frequency', 'D']]],],
                "Coin":{"Name":""}},
                "message":""}
    """
    result = {"error": 0, "data": "", "message": ""}
    language = request.__user__.get("language", "en")
    port_folio = await folios_dao.findFolio(folio_id)
    if not port_folio:
        result["error"] = 402
        result["message"] = _("402_NOT_EXIST", language)  # "This portfolio does not exist."
        return result

    user_id = request.__user__.get("referId", "")
    read = request.__user__.get("read", False)
    if user_id and int(user_id) != port_folio.user_id and not read:
        result["error"] = 408
        result["data"] = {}
        result["message"] = _("408_NOT_VIEW", language)  # "You do not have permission to view this page."
        return result

    db = Connection.getInstance()
    modify_at = toPreTimestamp(port_folio.modify_at, day_num=365)
    params = "ratios_%s"%language
    item = await db.get_cache(folio_id, "portfolio", params, modify_at=modify_at)
    if item:
        reportData = item
    else:
        reportData = await portfolio_ratios(port_folio, db, lang=language)

    result["data"] = reportData

    return result


@get('/coinai/get/reports/portfolio/optimization/{folio_id}',auth=True)
async def portfolio_optimization_report(folio_id, request, *, risk_fun=""):
    """
    :param folio_id:
    :param request:
    :return:
    {  "error":0,
       "data": { "port_optimizer":
                {'F': 3, 'Fun': 'var', 'Frontier': [
                                                        [
                                                         [5.665583147960494e-18, 0.36183516038544905, 3.469446951953614e-18, 0.0, 0.0, 0.638164839614551],
                                                         0.0052074245313212591, 0.055170652212638852
                                                       ],
                                                 ],
                'Factors': [{'Name': 'litecoin Index'},],
                'Regressions': [{'betas': [-0.055436397651691928, 0.55264489297011576, 0.52778631684958122]},
                                ],
                'Coins': [{'Name': 'litecoin', 'StrategyCode': 'Fund of Funds'},
                            ],
                'K': 6, 'AnnFactor': 365, 'NN': 0, 'MaxSharpeIDx': 13, 'MaxER': 9.3002802197802215,
                'Portfolio': {'folio_id': 'e5191468-46e5-11e8-a5da-0274604c7918', 'Name': 'Banca'},
                'N': 25},
                "bestFolio": 7
            }
       "message":""
    }
    """
    result = {"error": 0, "data": "", "message": ""}
    language = request.__user__.get("language", "en")
    db = Connection.getInstance()
    
    portfolio =  await db.get_portfolio(folio_id, recalc=False, modify_num=30)
    if not portfolio:
        result["error"] = 402
        result["message"] = _("402_NOT_EXIST", language)  # "This portfolio does not exist."
        return result

    user_id = portfolio.user_id

    userId = request.__user__.get("referId", "")
    read = request.__user__.get("read", False)
    if userId and int(userId) != user_id and not read:
        result["error"] = 408
        result["data"] = {}
        result["message"] = _("408_NOT_VIEW", language)  # "You do not have permission to view this page."
        return result

    params = risk_fun + language
    item = await db.get_cache(folio_id, "portfolio", "optimization", params, modify_at=portfolio.modify_at)
    if item:
        result_data = item
    else:
        modify_at = ""
        allocations = (portfolio.Allocations if isinstance(portfolio.Allocations,list) else json.loads(portfolio.Allocations.decode())) if portfolio else []
        coinids = [a['coin_id'] for a in allocations]
        refdata = await report_dao.findReferenceData('DefaultFactorModel')
        if refdata:
            modelcode = refdata.data
        else:
            modelcode = "BTC Factor"

        factor_model = await report_dao.findFactorModel(modelcode)
        factor_list = json.loads(factor_model.factors.decode()) if factor_model else []
        factors = await db.get_risk_factors(factor_list, modify_at, isPortfolio=True)
        factor_ts = [f.Performance for f in factors]

        eqweights = [1.0 / len(allocations) for _ in allocations]
        common_ts = await portfolio.calc_proforma(db, modify_at, eqweights, modify_num=30) if portfolio else []
        freq = get_frequency(common_ts)
        ann_factor = freq_map[freq]

        coins = await db.get_coins(user_id = user_id, coinids = coinids, modify_at=modify_at, get_ts=True)
        ers = [f.Performance.mean() for f in coins]
        max_er = max(ers)
        risk_fun = str(risk_fun)
        if risk_fun:
            min_fun = risk_fun if risk_fun in ["mdd", "var", "cvar"] else "var"
        else:
            min_fun = 'var'

        optimizer = Optimizer(coins, riskfun=min_fun)
        n_portfolios = 25
        frontier = optimizer.build_frontier(n_portfolios=n_portfolios)

        sharpes = [f[1] / f[2] for f in frontier]
        max_sharpe = max(sharpes)
        max_idx = [i for i in range(n_portfolios) if sharpes[i] == max_sharpe][0]

        # calculate factor models
        weights = [p[0] for p in frontier]
        proformas = []
        for w in weights:
            port_folio = await portfolio.calc_proforma(db, modify_at, w, modify_num=30)
            proformas.append(port_folio)

        regs = [RegressionAnalysis(p, factor_ts) for p in proformas]
        result_data = {"Frontier":toList(frontier),
                 "Portfolio":{"HashKey":portfolio.folio_id, "Name":portfolio.Name},
                 "N" : n_portfolios,
                 "NN" : 0,
                 "Coins" : [{"StrategyCode":"Coin of Coins", "Name": coin.Name} for coin in coins],
                 "K" : len(coins),
                 "F" : len(factors),
                 "Regressions":[{"betas":reg.betas}  for reg in regs],
                 "Factors":[{"Name":factor.Name} for factor in factors],
                 "Fun":min_fun,
                 "AnnFactor":ann_factor,
                 "MaxER":toDecimal(max_er * ann_factor),
                 "MaxSharpeIDx":max_idx,
                 "bestFolio":max_idx}

        await db.set_cache(folio_id, "portfolio", "optimization", params, data=result_data, modify_at=portfolio.modify_at)

    result['data'] = result_data

    return result


@get('/coinai/get/reports/portfolio/basic/{folio_id}',auth=False)
async def portfolio_basic_report(folio_id, request):
    """
    :param folio_id:
    :param request:
    :return:
        {'HistData': [(-0.19194666666666665, 3), (-0.15915333333333334, 2),],
        'Benchmarks': [],
        'ValueAtRisk': -0.12460853649585023,
        'N_Benchmarks': 0,
        'HistReturns': [[{'year': 2017, 'day': 2, 'month': 7}, 0.36553999999999998], [{'year': 2017, 'day': 2, 'month': 7}, 0.12615999999999999]],
        'UnderWater': [[{'year': 2017, 'day': 2, 'month': 7}, 0.0], [{'year': 2017, 'day': 3, 'month': 7}, 0.0]],
        'Data': [[{'year': 2017, 'day': 2, 'month': 7}, [1.36554]], [{'year': 2017, 'day': 2, 'month': 7}, [1.5378165264]]],
        'Columns': ['Coin 122fcfdc-46e6-11e8-8e76-0274604c7918'],
        'Coin': {'Name': 'Coin 122fcfdc-46e6-11e8-8e76-0274604c7918'}
        }
    """

    result = {"error": 0, "data": "", "message": ""}
    language = request.__user__.get("language", "en")
    db = Connection.getInstance()
    portfolio = await folios_dao.findFolio(folio_id)
    if not portfolio:
        result["error"] = 402
        result["message"] = _("402_NOT_EXIST", language)  # "This portfolio does not exist."
        return result

    params = "basic_%s"%language
    item = await db.get_cache(folio_id, "portfolio", params, modify_at=portfolio.modify_at)
    if item:
        res_data = item
    else:
        await folios_dao.read_folio(folio_id, portfolio)
        report = BasicReport(folio_id, portfolio.created_at)
        await report.analysis()
        res_data = {
            'Columns':report.vami_cols,
            'Data':report.vami_data_rate,
            'HistData':report.histogram_data,
            'HistReturns':report.hist_chart_data,
            'ValueAtRisk':report.var,
            'UnderWater':report.mdd_reses,
            'Benchmarks':report.benchmarks,
            'N_Benchmarks':len(report.benchmarks),
            'Coin':{"Name":"Portfolio"},
            "folio_id": folio_id
        }
        await db.set_cache(folio_id, "portfolio", params,  data=res_data, modify_at=portfolio.modify_at)

    result['data'] = res_data

    return result


@get('/coinai/get/reports/portfolio/ai/{folio_id}',auth=True)
async def portfolio_ai_report(folio_id, request, *, factor_code="", regime_name="", n_trials=100):
    """
    :param folio_id:
    :param request:
    :return:
    {'Results':[
            {'return_series':
                {'index': [1525062714373166000, 1527654714373166000,],
                'value': {1543552314373166000: 0.87184912319866414, 1527654714373166000: 0.0,}
                },
            'regime_series':
                {'index': [1525062714373166000, 1527654714373166000],
                'value': {1543552314373166000: 'Regime 0', 1527654714373166000: 'Regime 0'}
                }
            }
        ],
    'Coin': {'Name': 'Folio 122fcfdc-46e6-11e8-8e76-0274604c7918'},
    'RegimeModel': "ModelName",
    'MDDHist': [[-0.7495821095324473, 3], [-0.66629520847328649, 3]],
    'RegimeModels': [{'FactorModel': 'BANCA', 'NRegimes': 3, 'ModelName': 'Banca'}, ],
    'FactorModels': [{'Code': 'ChinaFactors', 'Factors': ['^litecoin', '^ethereum', '^bitcoin']}],
    'N': 100,
    'T': 12,
    'FactorModel': {'Code': 'ChinaFactors', 'Factors': ['^litecoin', '^ethereum', '^bitcoin']},
    'ReturnHist': [[11.571687790227044, 68], [23.501677066650903, 24]],
    'Percentiles': [[99, 99], [95, 95],]
    }
    """
    result = {"error": 0, "data": "", "message": ""}
    language = request.__user__.get("language", "en")
    db = Connection.getInstance()

    folio = await db.get_portfolio(folio_id, modify_num=182)
    if not folio:
        result["error"] = 402
        result["message"] = _("402_NOT_EXIST", language)  # "This portfolio does not exist."
        return result

    user_id = request.__user__.get("referId", "")
    read = request.__user__.get("read", False)
    if user_id and int(user_id) != folio.user_id and not read:
        result["error"] = 408
        result["data"] = {}
        result["message"] = _("408_NOT_VIEW", language)  # "You do not have permission to view this page."
        return result

    n_trials = n_trials if n_trials else 100
    if int(n_trials) > 500:
        result["error"] = 412
        result["message"] = _("412_NUMBER_TRIALS_500", language)  # "Number of trials cannot be greater than 500."
        return result

    modify_at = folio.modify_at if folio else ""
    """
        Monte Carlo simulatiaon is based on regime model and simulates movement
        of factors based on simulated regimes
    """

    all_regime_models = await db.get_regime_model_list()
    all_factor_models = await db.get_factor_models()

    # by default we simulate performance 12 months forward
    n_periods = 12
    if factor_code:
        factor_model_name = factor_code
    else:
        factor_model_name = all_factor_models[0]['code']

    if regime_name:
        regime_model_name = regime_name
    else:
        regime_model_name = all_regime_models[0]['model_name']

    n_trials = int(n_trials) if n_trials and int(n_trials) > 0 else 100  # need at least one trial
    regime_model = await db.get_regime_model(regime_model_name)
    factor_model = await db.get_factor_model(factor_model_name)
    factors = json.loads(factor_model.factors.decode()) if factor_model.factors else []
    factors = await db.get_risk_factors(factors, modify_at=modify_at)
    factor_ts = [f.Performance for f in factors]
    start_date = prev_eom(datetime.today())
    all_series = factor_ts.copy()

    performance_data = folio.folio_ts
    all_series.insert(0, performance_data)
    common_data = align_series(all_series)
    columns = common_data.columns

    # We estimate Coin's exposure to the factors so we can use the betas in simulations
    # In each period simlated Coin performance is E(R) = Alpha + Sum(B*RFactor)
    Y = common_data[columns[0]].values
    X = common_data[columns[1:]].values
    X = sm.add_constant(X)
    model = sm.OLS(Y, X)
    fit = model.fit()
    reg_results = list(fit.params)
    betas = reg_results[1:]
    alpha = betas[0]

    # Esg simulates factor performance over time
    esg = ESGSimulator(regime_model=regime_model, factors=factors,
                       n_trials=n_trials, n_periods=n_periods, start_date=start_date)

    esg.run_simulation()
    # Monte carlo applies betas to the ESG simulated factors
    mc = MonteCarlo(trials=esg.trials, betas=betas, alpha=alpha)
    trials = mc.trials
    returns = mc.returns
    mdds = mc.mdds
    returns = [ret for ret in returns if str(ret) != 'nan']
    mdds = [m for m in mdds if str(m) != 'nan']
    ret_hist = get_histogram(returns, True, 10)
    mdd_hist = get_histogram(mdds, False, -1)
    pcts = [99, 95, 75, 50, 25, 5, 0]
    pct_idx = [[p, int(p * 0.01 * n_trials)] for p in pcts]

    def series_data(trial_series):
        values = [str(val).split(".")[0].split("T")[0] for val in trial_series.index.values]
        to_regime_name = lambda v: regime_val.get(str(v),v)
        series_data = {
            "value": {val:to_regime_name(trial_series[val].values.tolist()[0]) \
                       if isinstance(trial_series[val].values.tolist()[0], str) else toDecimal(trial_series[val].values.tolist()[0])
                       for val in values},
            "index": values
        }
        return series_data

    trials_list = [
        {"regime_series": series_data(trial.regime_series),
         "return_series": series_data(trial.return_series)
         } for trial in trials
        ]

    res_data = {
                "Results":trials_list,
                "Coin":{"Name":folio.Name},
                "ReturnHist":ret_hist,
                "MDDHist":mdd_hist,
                "RegimeModels":all_regime_models,
                "RegimeModel":regime_model_name,
                "FactorModel":{"Code":factor_model.code},
                "FactorModels":all_factor_models,
                "N":n_trials,
                "T":n_periods,
                "Percentiles":pct_idx
            }

    result["data"] = res_data

    return result


@get('/coinai/get/reports/portfolio/style/{folio_id}',auth=True)
async def portfolio_style_report(folio_id, request, *,factor_code=""):
    """
    :param folio_id:
    :param request:
    :return:
    {
        'T': 290,
        'rolling_reg': [[{
            'month': 7,
            'day': 25,
            'year': 2017
        }, {
            'crisk': [0.22442397676756218, 0.36286683843005429, 0.10656616900823793, 0.3061430157941456],
            'betas': [0.50568919158688619, 0.52937700850121105, 0.24701484550270511]
        }]],
        'common_data': {
            'iloc': [[-0.035109999999999975, -0.028000000000000025, -0.03859999999999997, -0.03249999999999997],
                    [0.0044200000000000905, 0.035800000000000054, -0.016199999999999992, -0.019399999999999973]
                    ]
        },
        'reg_analysis': {
            'crisk': [0.20352092123670679, 0.40218050447543346, 0.20052533187549684, 0.19377324241236293],
            'betas': [0.22222585120741567, 0.49974080939828847, 0.32340341154592933],
            'rsq': 0.80344666532009268
        },
        'N': 4,
        'factor_names': ['litecoin Index', 'ethereum Index', 'bitcoin Index', 'Unexplained']
    }
    """
    result = {"error": 0, "data": "", "message": ""}
    language = request.__user__.get("language", "en")

    db = Connection.getInstance()
    folio = await folios_dao.findFolio(folio_id)
    if not folio:
        result["error"] = 402
        result["message"] = _("402_NOT_EXIST", language)  # "This portfolio does not exist."
        return result

    userId = request.__user__.get("referId", "")
    read = request.__user__.get("read", False)
    if userId and int(userId) != folio.user_id and not read:
        result["error"] = 408
        result["data"] = {}
        result["message"] = _("408_NOT_VIEW", language)  # "You do not have permission to view this page."
        return result

    params = factor_code + language
    item = await db.get_cache(folio_id, "portfolio", "style", params=params, modify_at=folio.modify_at)
    if item:
        res_data = item
    else:
        factormodels = await db.get_factor_models()
        if factor_code:
            model_code = factor_code
            factormodel = await db.get_factor_model(model_code)
            tickers = json.loads(factormodel['factors'].decode()) if factormodel['factors'] else []
        else:
            model_code = factormodels[0]['code']
            if len(factormodels) > 0:
                tickers = json.loads(factormodels[0]['factors'].decode()) if factormodels[0]['factors'] else []
            else:
                tickers = ["^bitcoin", "^ethereum", "^eos", "^ripple"]

        style = StyleAnalysis(folio_id, tickers, started_at=folio.created_at)
        await style.analysis()

        ilocs = style.common_data.values.tolist()
        ilocs = [[toDecimal(il) for il in iloc] if isinstance(iloc, list) else toDecimal(iloc)  for iloc in ilocs]
        Results = {"N":style.N,
                   "factor_names":style.factor_names,
                   "reg_analysis":{
                       "betas":style.reg_analysis.betas,
                       "rsq":toDecimal(style.reg_analysis.rsq),
                       "crisk":[toDecimal(crisk) for crisk in style.reg_analysis.crisk]
                   },
                   "rolling_reg":style.rolling_reg,
                   "common_data":{
                       "iloc":ilocs
                   },
                   "T":style.T}

        res_data = {
            "Results":Results,
            "IsPortfolio":1,
            "Coin":{"Name":style.item.Name, "HashKey":style.item.folio_id},
            "FactorModels":[{"Code":factor["code"]} for factor in factormodels],
            "SelectedModel":model_code
        }
        await db.set_cache(folio_id, "portfolio", "style", params=params, data=res_data, modify_at=folio.modify_at)

    result["data"] = res_data

    return result

@get('/coinai/get/reports/portfolio/benchmark/{folio_id}',auth=True)
async def portfolio_benchmark_report(folio_id, request):
    """
    :param folio_id:
    :param request:
    :return:
    {
        'captures': {
            'bench_up': 0.056619148936170212,
            'perf_bench_dn': 0.0,
            'dn_capture': 1.0,
            'up_capture': 1.0,
            'perf_bench_up': 0.0,
            'bench_dn': -0.04098352272727273
        },
        'coin_stats': {
            'ann_return': 4.7637332158367682,
            'ann_std': 1.1119499663591519
        },
        'benchmark': {
            'Name': 'ethereum Index'
        },
        'corr_analysis': {
            'XY': [
                [3.18000000e-02, 3.18000000e-02],
                [-2.80000000e-03, -2.80000000e-03]
            ],
            'T': 364,
            'corr': 1.0
        },
        'bench_stats': {
            'ann_return': 4.7637332158367682,
            'ann_std': 1.1119499663591519
        },
        'reg_capm': {
            'alpha': -8.4567769453869346e-18,
            'betas': [1.0000000000000009]
        },
        'reg_tmy': {
            'alpha': -1.1492543028346347e-17,
            'betas': [1.0000000000000009, 5.5511151231257827e-17]
        }
    }
    """
    result = {"error": 0, "data": "", "message": ""}
    language = request.__user__.get("language", "en")

    db = Connection.getInstance()
    port_folio = await db.get_portfolio(folio_id, modify_num=30)
    if not port_folio:
        result["error"] = 402
        result["message"] = _("402_NOT_EXIST", language)  # "This portfolio does not exist."
        return result

    userId = request.__user__.get("referId", "")
    read = request.__user__.get("read", False)
    if userId and int(userId) != port_folio.user_id and not read:
        result["error"] = 408
        result["data"] = {}
        result["message"] = _("408_NOT_VIEW", language)  # "You do not have permission to view this page."
        return result


    item = await db.get_cache(folio_id, "portfolio", "benchmark", modify_at=port_folio.modify_at)
    if item:
        res_data = item
    else:
        modify_time = port_folio.created_at
        benchmarks = await get_benchmarks(db, modify_time)
        if benchmarks:
            if port_folio.Name in benchmarks:
                selected_benchmark = benchmarks[port_folio.Name].ticker
            else:
                selected_benchmark = "^bitcoin"
        else:
            selected_benchmark = "^bitcoin"

        ba = BenchmarkAnalysis(port_folio, selected_benchmark, modify_time)
        await ba.analysis()

        XY = ba.corr_analysis.XY.tolist()
        x_y = [[toDecimal(d) for d in xy] if isinstance(xy,list) else toDecimal(xy) for xy in XY]
        benchmarkAnalysis = {
            "corr_analysis":{"corr":toDecimal(ba.corr_analysis.corr),"T":ba.corr_analysis.T, "XY":x_y},
            "reg_capm":{"betas":ba.reg_capm.betas, "alpha":toDecimal(ba.reg_capm.alpha)},
            "reg_tmy": {"betas":ba.reg_tmy.betas, "alpha":toDecimal(ba.reg_tmy.alpha)},
            "coin_stats": {"ann_return":toDecimal(ba.coin_stats.ann_return), "ann_std":toDecimal(ba.coin_stats.ann_std)},
            "benchmark": {"Name":ba.benchmark.Name},
            "bench_stats": {"ann_return":toDecimal(ba.bench_stats.ann_return), "ann_std":toDecimal(ba.bench_stats.ann_std)},
            "captures": {"up_capture":toDecimal(ba.captures.up_capture),"dn_capture":toDecimal(ba.captures.dn_capture),
                         "perf_bench_up":toDecimal(ba.captures.perf_bench_up), "bench_up":toDecimal(ba.captures.bench_up),
                         "perf_bench_dn": toDecimal(ba.captures.perf_bench_dn), "bench_dn": toDecimal(ba.captures.bench_dn)}
        }

        benchmarks = [{"Ticker":bench.ticker, "Name":bench.Name } for bench in benchmarks.values()]
        res_data = {
            "Coin":{"Name": port_folio.Name},
            "Benchmarks": benchmarks,
            "SelectedBenchmark":selected_benchmark,
            "BenchmarkAnalysis":benchmarkAnalysis
        }

        await db.set_cache(folio_id, "portfolio", "benchmark",  data=res_data, modify_at=port_folio.modify_at)

    result["data"] = res_data

    return result


@get('/coinai/get/reports/portfolio/risk/{folio_id}',auth=True)
async def portfolio_risk_report(folio_id, request):
    """
    :param folio_id:
    :param request:
    :return:
     {
        "N": 11,
        "Coins": [{"Name":"asdasd"},],
        "crisk": [0.21132,],
        "c_ret": [0.214],
        "portfolio": [{"Name":"sadad"},],
        "marginal_vars": [213,12,-21],
    }
    """
    result = {"error": 0, "data": "", "message": ""}
    language = request.__user__.get("language", "en")

    db = Connection.getInstance()
    folio = await db.get_portfolio(folio_id, get_coins=True, recalc=False, modify_num=365)
    if not folio:
        result["error"] = 402
        result["message"] = _("402_NOT_EXIST", language)  # "This portfolio does not exist."
        return result

    userId = request.__user__.get("referId", "")
    read = request.__user__.get("read", False)
    if userId and int(userId) != folio.user_id and not read:
        result["error"] = 408
        result["data"] = {}
        result["message"] = _("408_NOT_VIEW", language)  # "You do not have permission to view this page."
        return result

    item = await db.get_cache(folio_id, "portfolio", "risk", modify_at=folio.modify_at)
    if item:
        attrib_dict = item
    else:
        attrib = PortfolioAttribution(portfolio=folio, db=db)
        await attrib.analysis()
        attrib_dict = {
            "N": attrib.N,
            "Coins": [{"Name":allocs["coin_name"]} for allocs in attrib.allocs],
            "crisk": attrib.crisk,
            "c_ret": attrib.c_ret,
            "portfolio": {"Name":folio.Name},
            "marginal_vars": attrib.marginal_vars,
        }

        await db.set_cache(folio_id, "portfolio", "risk",  data=attrib_dict, modify_at=folio.modify_at)

    result["data"] = attrib_dict

    return result


@get('/coinai/get/reports/portfolio/versus/{folio_id}',auth=True)
async def portfolio_vs_report(folio_id, request, *, factor_code="", regime_name=""):
    """
    :param folio_id:
    :param request:
    :return:
    {
       "PeerStats":{
            # 'folio_stats': {
            #     'sharpe': 1.9435799482112084,
            #     'var_adj': -0.095261830412716617,
            #     'kurt': 8.666386688264108,
            #     'maxdd': -0.31881355288863389,
            #     'serr_corr': 0.079032817063763416,
            #     'ann_std': 0.5373425121149894,
            #     'var': -0.062432195371790997,
            #     'skew': 1.3172575776759732,
            #     'ann_return': 1.4660592339446179,
            #     'sortino': 5.3029138594020377
            # },
            'peer_stats': [{
                'Name': 'tron',
                'peer_style': {
                    'betas': [-0.19691962763951587, 0.93283755974439297, 0.78409118999864891]
                },
                'HashKey': '3690984c-4877-11e8-9d8f-0274604c7918',
                'peer_stats': {
                    'sharpe': 2.4056202827161113,
                    'var_adj': -0.5973979678193474,
                    'kurt': 15.472396459990355,
                    'maxdd': -0.87144271865389356,
                    'serr_corr': 0.063223450090541602,
                    'ann_std': 3.0989834219174552,
                    'var': -0.35433405543671731,
                    'skew': 2.811720803017995,
                    'ann_return': 39.514768733176645,
                    'sortino': 34.789450774121697
                },
                'corr': 0.27299322542398774,
                'index': 8,
                'factors': [{
                    'Name': 'litecoin Index'
                }, {
                    'Name': 'ethereum Index'
                }, {
                    'Name': 'bitcoin Index'
                }],
                'regime_stats': {'regimes': ['Regime 2',],
                                 'avg': {'iloc': [
                                             [0.009640490460859701, 0.009640490460859701]
                                             ]
                                        },
                                 'N': 1
                                 }
            },]
        },
        'Coin': {'Name': 'Folio 122fcfdc-46e6-11e8-8e76-0274604c7918'},
        'RegimeModel': "ModelName",
        'RegimeModels': [{'FactorModel': 'BANCA', 'NRegimes': 3, 'ModelName': 'Banca'}, ],
        'FactorModels': [{'Code': 'ChinaFactors', 'Factors': ['^litecoin', '^ethereum', '^bitcoin']}],
        'FactorModel': {'Code': 'ChinaFactors', 'Factors': ['^litecoin', '^ethereum', '^bitcoin']},
        'NFactors': 12,
    }
    """
    result = {"error": 0, "data": "", "message": ""}
    language = request.__user__.get("language", "en")

    db = Connection()
    folio = await folios_dao.findFolio(folio_id)
    if not folio:
        result["error"] = 402
        result["message"] = _("402_NOT_EXIST", language)  # "This portfolio does not exist."
        return result

    userid = request.__user__.get("referId", "")
    read = request.__user__.get("read", False)
    if userid and int(userid) != folio.user_id and not read:
        result["error"] = 408
        result["data"] = {}
        result["message"] = _("408_NOT_VIEW", language)  # "You do not have permission to view this page."
        return result

    modify_at = await db.get_portfolio_modify(userid)
    params_str = "%s%s"%(userid, str(factor_code))
    item = await db.get_cache(folio_id, "portfolio", "versus", params=params_str, modify_at=folio.modify_at, extra=modify_at)
    if item:
        res_data = item
    else:
        all_regime_models = await db.get_regime_model_list()
        all_factor_models = await db.get_factor_models()
        if regime_name:
            regime_model_name = regime_name
        else:
            regime_model_name = all_regime_models[0]['model_name']

        if factor_code:
            factor_model_name = factor_code
        else:
            factor_model_name = all_factor_models[0]['code']
        regime_model = await db.get_regime_model(regime_model_name)
        factor_model = await db.get_factor_model(factor_model_name)
        if not factor_model:
            result["error"] = 405
            result["message"] = _("405_INVAID_CODE", language)  # "Invaid code."
            return result

        folio = await db.get_portfolio(folio_id)
        if not userid:
            userid = folio.user_id
        stats = PeerAnalysis(folio, userid,
                             model_ticker=factor_model['code'],
                             regime_model_name=regime_model.model_name)
        await stats.analysis()
        tickers = json.loads(factor_model.factors.decode())

        peer_stats = {"peer_stats":
                          [
                              {
                                  "index":peer.index, "HashKey":peer.HashKey, "Name":peer.Name,
                                  "corr": toDecimal(peer.corr),
                                  "factors":[{"Name":factor.Name}  for factor in peer.factors],
                                  "peer_style":{"betas": peer.peer_style.betas},
                                  "peer_stats":{
                                      "ann_return":toDecimal(peer.peer_stats.ann_return),
                                      "ann_std":toDecimal(peer.peer_stats.ann_std),
                                      "maxdd": toDecimal(peer.peer_stats.maxdd),
                                      "serr_corr": toDecimal(peer.peer_stats.serr_corr),
                                      "skew": toDecimal(peer.peer_stats.skew),
                                      "kurt": toDecimal(peer.peer_stats.kurt),
                                      "sharpe": toDecimal(peer.peer_stats.sharpe),
                                      "sortino": toDecimal(peer.peer_stats.sortino),
                                      "var": toDecimal(peer.peer_stats.var),
                                      "var_adj": toDecimal(peer.peer_stats.var_adj),
                                      "worst":toDecimal(peer.peer_stats.worst),
                                      "mean": toDecimal(peer.peer_stats.mean),
                                      "std": toDecimal(peer.peer_stats.std),
                                      "best": toDecimal(peer.peer_stats.best),
                                      "socre":toDecimal(peer.peer_stats.socre),
                                      "entire_return": toDecimal(peer.entire_return)
                                  },
                                  "regime_stats": {"regimes":peer.regime_stats.regimes,
                                                      "avg":{"iloc":[[toDecimal(il) for il in iloc] if isinstance(iloc, list) else toDecimal(iloc) \
                                                                     for iloc in peer.regime_stats.avg.values.tolist()]},
                                                      "N":peer.regime_stats.N
                                                   }
                              } for peer in stats.peer_stats
                          ]
                      }

        res_data = {
           "PeerStats":peer_stats,
            "Coin":{"Name":folio.Name},
            "FactorModels":all_factor_models,
            "FactorModel":{"Code":factor_model.code},
            "RegimeModels":all_regime_models,
            "RegimeModel":regime_model.model_name,
            "NFactors":len(tickers)
        }

        await db.set_cache(folio_id, "portfolio", "versus",  params=params_str,
                                data=res_data, modify_at=folio.modify_at, extra=modify_at)

    result["data"] = res_data

    return result

@get('/coinai/get/reports/coins/ai/{coin_id}',auth=False)
async def coin_ai_report(coin_id, request, *, factor_code="", regime_name="", n_trials=100):
    """
    :param coin_id:
    :param request:
    :return:
        {'Results':[
                {'return_series':
                    {'index': [1525062714373166000, 1527654714373166000,],
                    'value': {1543552314373166000: 0.87184912319866414, 1527654714373166000: 0.0,}
                    },
                'regime_series':
                    {'index': [1525062714373166000, 1527654714373166000],
                    'value': {1543552314373166000: 'Regime 0', 1527654714373166000: 'Regime 0'}
                    }
                }
            ],
            'Coin': {'Name': 'Folio 122fcfdc-46e6-11e8-8e76-0274604c7918'},
            'RegimeModel': "ModelName",
            'MDDHist': [[-0.7495821095324473, 3], [-0.66629520847328649, 3]],
            'RegimeModels': [{'FactorModel': 'BANCA', 'NRegimes': 3, 'ModelName': 'Banca'}, ],
            'FactorModels': [{'Code': 'ChinaFactors', 'Factors': ['^litecoin', '^ethereum', '^bitcoin']}],
            'N': 100,
            'T': 12,
            'FactorModel': {'Code': 'ChinaFactors', 'Factors': ['^litecoin', '^ethereum', '^bitcoin']},
            'ReturnHist': [[11.571687790227044, 68], [23.501677066650903, 24]],
            'Percentiles': [[99, 99], [95, 95],]
        }
    """
    result = {"error": 0, "data": "", "message": ""}
    language = request.__user__.get("language", "en")

    db = Connection.getInstance()
    coin = await db.get_coin(coin_id)
    if not coin:
        result["error"] = 411
        result["message"] = _("411_COIN_NOT_EXIST", language)  # "This coin does not exist."
        return result

    n_trials = n_trials if n_trials else 100
    if int(n_trials) > 500:
        result["error"] = 412
        result["message"] = _("412_NUMBER_TRIALS_500", language)  # "Number of trials cannot be greater than 500."
        return result


    """
        Monte Carlo simulatiaon is based on regime model and simulates movement
        of factors based on simulated regimes
   """
    all_regime_models = await db.get_regime_model_list()
    all_factor_models = await db.get_factor_models()

    # by default we simulate performance 12 months forward
    n_periods = 12

    if factor_code:
        factor_model_name = factor_code
    else:
        factor_model_name = all_factor_models[0]['code']

    if regime_name:
        regime_model_name = regime_name
    else:
        regime_model_name = all_regime_models[0]['model_name']

    n_trials = int(n_trials) if n_trials and int(n_trials) > 0 else 100  # need at least one trial
    regime_model = await db.get_regime_model(regime_model_name)
    factor_model = await db.get_factor_model(factor_model_name)
    factors = json.loads(factor_model.factors.decode()) if factor_model.factors else []
    factors = await db.get_risk_factors(factors)
    factor_ts = [f.Performance for f in factors]
    start_date = prev_eom(datetime.today())
    all_series = factor_ts.copy()

    all_series.insert(0, coin.Performance)
    common_data = align_series(all_series)
    columns = common_data.columns

    # We estimate Coin's exposure to the factors so we can use the betas in simulations
    # In each period simlated Coin performance is E(R) = Alpha + Sum(B*RFactor)
    Y = common_data[columns[0]].values
    X = common_data[columns[1:]].values
    X = sm.add_constant(X)
    model = sm.OLS(Y, X)
    fit = model.fit()
    reg_results = list(fit.params)
    betas = reg_results[1:]
    alpha = betas[0]

    # Esg simulates factor performance over time
    esg = ESGSimulator(regime_model=regime_model, factors=factors,
                       n_trials=n_trials, n_periods=n_periods, start_date=start_date)

    esg.run_simulation()
    # Monte carlo applies betas to the ESG simulated factors
    mc = MonteCarlo(trials=esg.trials, betas=betas, alpha=alpha)
    trials = mc.trials
    returns = mc.returns
    mdds = mc.mdds
    returns = [ret for ret in returns if str(ret) != 'nan']
    mdds = [m for m in mdds if str(m) != 'nan']
    ret_hist = get_histogram(returns, True, 10)
    mdd_hist = get_histogram(mdds, False, -1)
    pcts = [99, 95, 75, 50, 25, 5, 0]
    pct_idx = [[p, int(p * 0.01 * n_trials)] for p in pcts]

    def series_data(trial_series):
        values = [str(val).split(".")[0].split("T")[0] for val in trial_series.index.values]
        to_regime_name = lambda v: regime_val.get(str(v), v)
        series_data = {
            "value": {val:to_regime_name(trial_series[val].values.tolist()[0]) if isinstance(trial_series[val].values.tolist()[0], str) \
                             else toDecimal(trial_series[val].values.tolist()[0])
                                for val in values},
            "index": values
        }
        return series_data

    trials_list = [
        {"regime_series": series_data(trial.regime_series),
         "return_series": series_data(trial.return_series)
         } for trial in trials
        ]

    res_data = {
        "Results": trials_list,
        "Coin": {"Name": coin.Name},
        "ReturnHist": ret_hist,
        "MDDHist": mdd_hist,
        "RegimeModels": all_regime_models,
        "RegimeModel": regime_model_name,
        "FactorModel": {"Code": factor_model.code},
        "FactorModels": all_factor_models,
        "N": n_trials,
        "T": n_periods,
        "Percentiles": pct_idx
    }

    result["data"] = res_data

    return result


@get('/coinai/get/reports/coins/basic/{coin_id}',auth=False)
async def coin_basic_report(coin_id, request):
    """
    :param coin_id:
    :param request:
    :return:
    {'HistData': [(-0.19194666666666665, 3), (-0.15915333333333334, 2),],
        'Benchmarks': [],
        'ValueAtRisk': -0.12460853649585023,
        'N_Benchmarks': 0,
        'HistReturns': [[{'year': 2017, 'day': 2, 'month': 7}, 0.36553999999999998], [{'year': 2017, 'day': 2, 'month': 7}, 0.12615999999999999]],
        'UnderWater': [[{'year': 2017, 'day': 2, 'month': 7}, 0.0], [{'year': 2017, 'day': 3, 'month': 7}, 0.0]],
        'Data': [[{'year': 2017, 'day': 2, 'month': 7}, [1.36554]], [{'year': 2017, 'day': 2, 'month': 7}, [1.5378165264]]],
        'Columns': ['Coin 122fcfdc-46e6-11e8-8e76-0274604c7918'],
        'Coin': {'Name': 'Coin 122fcfdc-46e6-11e8-8e76-0274604c7918'}
        }
    """
    result = {"error": 0, "data": "", "message": ""}
    language = request.__user__.get("language", "en")

    db = Connection.getInstance()
    coin = await db.get_coin(coin_id)
    if not coin:
        result["error"] = 411
        result["message"] = _("411_COIN_NOT_EXIST", language)  # "This coin does not exist."
        return result

    params = "basic_%s"%language
    item = await db.get_cache(coin_id, "coins", params)
    if item:
        res_data = item
    else:
        report = BasicReport(coin_id, isPortFolio=False)
        await report.analysis()
        res_data = {
            'Columns': report.vami_cols,
            'Data': report.vami_data,
            'HistData': report.histogram_data,
            'HistReturns': report.hist_chart_data,
            'ValueAtRisk': report.var,
            'UnderWater': report.mdd_reses,
            'Benchmarks': report.benchmarks,
            'N_Benchmarks': len(report.benchmarks),
            'Coin': {"Name":coin.Name}
        }
        await db.set_cache(coin_id, "coins", params, data=res_data)

    result["data"] = res_data

    return result


@get('/coinai/get/reports/coins/ratios/{coin_id}',auth=False)
async def coin_ratio_report(coin_id, request):
    """
    :param coin_id:
    :param request:
    :return:
    {
        "ResultsAll": [["Number of Periods","290"],["Frequency","D"],["Number of Periods","290"],["Frequency","D"]],
        "RollResults": [["20",[['Number of Periods', '20'], ['Frequency', 'D']]],],
        "Coin": {"Name": "222"}
      }
    """
    result = {"error": 0, "data": "", "message": ""}
    language = request.__user__.get("language", "en")

    db = Connection.getInstance()
    coin = await db.get_coin(coin_id)
    if not coin:
        result["error"] = 411
        result["message"] = _("411_COIN_NOT_EXIST", language)  # "This coin does not exist."
        return result

    params = "ratios_%s" % language
    item = await db.get_cache(coin_id, "coins", params)
    if item:
        res_data = item
    else:
        fts = coin.Performance
        T = len(fts)
        rf_item = await report_dao.findReferenceData('Risk Free Rate')
        if rf_item:
            rf = float(rf_item.data) * 0.01
        else:
            rf = 0

        stats_all = BasicStats(fts, risk_free=0)
        helper = StatsHelper(lang=language)
        roll_windows = windows[stats_all.freq[0]]
        roll_results = []
        for w in roll_windows:
            if T >= w:
                roll_fts = fts[-1 * w:]
                roll_results.append([w, helper.help(BasicStats(roll_fts, risk_free=rf))])

        res_data = {
            'ResultsAll': helper.help(stats_all),
            'RollResults': roll_results,
            'Coin': {"Name":coin.Name}
        }
        await db.set_cache(coin_id, "coins", params, data=res_data)

    result["data"] = res_data

    return result


@get('/coinai/get/reports/coins/versus/{coin_id}',auth=True)
async def coin_vs_report(coin_id, request, *, factor_code="", regime_name=""):
    """
    :param coin_id:
    :param request:
    :return:
    {
       "PeerStats":{
            'peer_stats': [{
                'Name': 'tron',
                'peer_style': {
                    'betas': [-0.19691962763951587, 0.93283755974439297, 0.78409118999864891]
                },
                'HashKey': '3690984c-4877-11e8-9d8f-0274604c7918',
                'peer_stats': {
                    'sharpe': 2.4056202827161113,
                    'var_adj': -0.5973979678193474,
                    'kurt': 15.472396459990355,
                    'maxdd': -0.87144271865389356,
                    'serr_corr': 0.063223450090541602,
                    'ann_std': 3.0989834219174552,
                    'var': -0.35433405543671731,
                    'skew': 2.811720803017995,
                    'ann_return': 39.514768733176645,
                    'sortino': 34.789450774121697
                },
                'corr': 0.27299322542398774,
                'index': 8,
                'factors': [{
                    'Name': 'litecoin Index'
                }, {
                    'Name': 'ethereum Index'
                }, {
                    'Name': 'bitcoin Index'
                }],
                'regime_stats': {'regimes': ['Regime 2',],
                                 'avg': {'iloc': [
                                             [0.009640490460859701, 0.009640490460859701]
                                             ]
                                        },
                                 'N': 1
                                 }
            },]
        },
        'Coin': {'Name': 'Coin 122fcfdc-46e6-11e8-8e76-0274604c7918'},
        'RegimeModel': "ModelName",
        'RegimeModels': [{'FactorModel': 'BANCA', 'NRegimes': 3, 'ModelName': 'Banca'}, ],
        'FactorModels': [{'Code': 'ChinaFactors', 'Factors': ['^litecoin', '^ethereum', '^bitcoin']}],
        'FactorModel': {'Code': 'ChinaFactors', 'Factors': ['^litecoin', '^ethereum', '^bitcoin']},
        'NFactors': 12,
    }
    """
    result = {"error": 0, "data": "", "message": ""}
    language = request.__user__.get("language", "en")

    db = Connection()
    coin_obj = await db.get_coin(coin_id, get_ts=True)
    if not coin_obj:
        result["error"] = 411
        result["message"] = _("411_COIN_NOT_EXIST", language)  # "This coin does not exist."
        return result

    modify_dates = db.get_hotCoins_dates()
    params_str = "%s%s" % (str(regime_name), str(factor_code))
    item = await db.get_cache(coin_id, "coins", "versus", params=params_str, modify_at=coin_obj.modify_at,
                                   extra=modify_dates)
    if item:
        res_data = item
    else:
        all_regime_models = await db.get_regime_model_list()
        all_factor_models = await db.get_factor_models()

        if regime_name:
            regime_model_name = regime_name
        else:
            regime_model_name = all_regime_models[0]['model_name']

        if factor_code:
            factor_model_name = factor_code
        else:
            factor_model_name = all_factor_models[0]['code']

        regime_model = await db.get_regime_model(regime_model_name)
        factor_model = await db.get_factor_model(factor_model_name)
        if not factor_model:
            result["error"] = 405
            result["message"] = _("405_INVAID_CODE", language)  # "Invaid code."
            return result

        stats = PeerAnalysis(coin_obj, "",
                             model_ticker=factor_model['code'],
                             regime_model_name=regime_model.model_name)
        await stats.analysis()
        tickers = json.loads(factor_model.factors.decode())

        peer_stats = {"peer_stats":
                          [
                              {
                                  "index":peer.index, "HashKey":peer.HashKey, "Name":peer.Name,
                                  "corr": toDecimal(peer.corr),
                                  "factors":[{"Name":factor.Name}  for factor in peer.factors],
                                  "peer_style":{"betas": peer.peer_style.betas},
                                  "peer_stats":{
                                      "ann_return":toDecimal(peer.peer_stats.ann_return),
                                      "ann_std":toDecimal(peer.peer_stats.ann_std),
                                      "maxdd": toDecimal(peer.peer_stats.maxdd),
                                      "serr_corr": toDecimal(peer.peer_stats.serr_corr),
                                      "skew": toDecimal(peer.peer_stats.skew),
                                      "kurt": toDecimal(peer.peer_stats.kurt),
                                      "sharpe": toDecimal(peer.peer_stats.sharpe),
                                      "sortino": toDecimal(peer.peer_stats.sortino),
                                      "var": toDecimal(peer.peer_stats.var),
                                      "var_adj": toDecimal(peer.peer_stats.var_adj),
                                      "worst":toDecimal(peer.peer_stats.worst),
                                      "mean": toDecimal(peer.peer_stats.mean),
                                      "std": toDecimal(peer.peer_stats.std),
                                      "best": toDecimal(peer.peer_stats.best),
                                      "socre":toDecimal(peer.peer_stats.socre),
                                      "entire_return": toDecimal(peer.entire_return)
                                  },
                                  "regime_stats": {"regimes":peer.regime_stats.regimes,
                                                      "avg":{"iloc":[[toDecimal(il) for il in iloc] if isinstance(iloc, list) else toDecimal(iloc) \
                                                                     for iloc in peer.regime_stats.avg.values.tolist()]},
                                                      "N":peer.regime_stats.N
                                                   }
                              } for peer in stats.peer_stats
                          ]
                      }

        res_data = {
           "PeerStats":peer_stats,
            "Coin":{"Name":coin_obj.Name},
            "FactorModels":all_factor_models,
            "FactorModel":{"Code":factor_model.code},
            "RegimeModels":all_regime_models,
            "RegimeModel":regime_model.model_name,
            "NFactors":len(tickers)
        }

        await db.set_cache(coin_id, "coins", "versus",  params=params_str,
                                data=res_data, modify_at=coin_obj.modify_at, extra=modify_dates)

    result["data"] = res_data

    return result
