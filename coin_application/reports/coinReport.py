import time
import pandas as pd
import statsmodels.api as sm

from datetime import datetime
from numpy import histogram
from pandas import DataFrame, Series, np
from analytics.basicstats import BasicStats
from analytics.capture_ratios import CaptureRatios
from analytics.correlation_analysis import CorrelationAnalysis
from analytics.helper import StatsHelper
from analytics.regression_analysis import RegressionAnalysis
from analytics.time_series import align_series

from coin_application.portfolios import dao as folios_dao
from coin_application.reports import dao as report_dao
from datalib.coin import CoinPerformance
from datalib.datalib import Connection
from lib.utils import toDecimal, getErrorMsg, toPreTimestamp,  _
from logger.client import error
from settings import windows

f2d = lambda a: [round(toDecimal(x),4) for x in a]


"""
    Calculate non-linear sensitivity / convexity regression
"""
def calc_tmy(fts, benchts):
    common_data = align_series([fts, benchts])
    common_data.columns = ['Y', 'X']
    common_data['XY'] = common_data['X'] ** 2
    y = common_data.iloc[:, 0].values
    x = common_data.iloc[:, 1:].values
    x = sm.add_constant(x)

    model = sm.OLS(y, x)
    res = model.fit()
    return res.params


def get_histogram(values, gt=True, val=10):
    """
        Calculate Histogram
    """
    cnt, bins = histogram(values, bins='sqrt')
    datas = list([toDecimal(b), int(c)] for b, c in zip(bins[1:], cnt))
    data_list = []
    val_num = 0
    per = 0
    for d in datas:
        if gt:
            if val < float(d[0]):
                per = 9.999
                val_num += int(d[1])
            else:
                data_list.append(d)
        else:
            if val > float(d[0]):
                per = -0.9999
                val_num += int(d[1])
            else:
                data_list.append(d)
    data_list.append([toDecimal(per), int(val_num)])
    return data_list


async def get_benchmarks(db=None, modify_time=time.time()):
    """
    returns list of benchmarks
    """
    if not db:
        db = Connection.getInstance()
    benchdata = await report_dao.findReferenceData("DefaultBenchmarks")
    if benchdata:
        data_dict = {}
        for t in benchdata.data.decode().split(','):
            data_dict[t.split("^")[-1]] = await db.get_risk_factor(t.strip(), modify_time)
        return data_dict
    else:
        return {}

def calculate_fts(fts=[], dates=[]):

    if fts:
        pre_fts = [100]
        new_fts = []
        pre_val = 100
        for index,ft in enumerate(fts[1:]):
            pre_fts.append(pre_val*(ft+1))
            pre_val = pre_val * (ft + 1)
        pre_fts.reverse()
        for index, ft in enumerate(pre_fts):
            if index < len(pre_fts) - 1:
                val = float(round(float((ft - pre_fts[index+1]) / pre_fts[index+1]), 5))
                new_fts.append(val)
            else:
                new_fts.append(0.0)
        new_fts.reverse()
        fts = new_fts
        week_ser_fts = Series(data=fts[-7:], index=dates[-7:], name="")
        week_mdd_ser = BasicStats.under_water_series(week_ser_fts)
        week_max_drawdown = min(week_mdd_ser)
        vami=BasicStats.vami_arr(week_ser_fts)
        day_7_history = vami[-1] - 1
        ser_fts = Series(data=fts, index=dates, name="")
        mdd_ser = BasicStats.under_water_series(ser_fts)
        total_max_drawdown = min(mdd_ser)
        vami = BasicStats.vami_arr(ser_fts)
        entire_history = vami[-1] - 1
        week_fts = fts[-7:]
        week_volatility = np.std(week_fts)
        total_volatility = np.std(fts)
        
        return {"week_volatility": "%s%%" % str(round(week_volatility*100, 3)),
                "week_max_drawdown": "%s%%" % str(round(week_max_drawdown, 3)),
                "total_volatility": "%s%%" % str(round(total_volatility*100, 3)),
                "total_max_drawdown": "%s%%" % str(round(total_max_drawdown, 3)),
                "entire_history": float(round(entire_history*100, 4)),
                "day_7_history":float(round(day_7_history*100, 4))
                }
    else:
        return {}


async def portfolio_ratios(port_folio=None, folio_id="", db=None, lang="en"):

    try:
        if not db:
            db = Connection.getInstance()

        if not port_folio:
            if folio_id:
                port_folio = await folios_dao.findFolio(folio_id)
                if not port_folio:
                    return None
            else:
                return None

        helper = StatsHelper(lang=lang)
        proforma = await folios_dao.GetFolioPerformance(port_folio.id)
        if proforma:
            fts = proforma["pre_data"]["data"]
            now_data = [nowData["data"] for nowData in proforma["now_data"]]
            now_fts = []
            for d in now_data:
                fts.extend(d)
                now_fts.extend(d)

            prof_fts = [perf["NetReturn"] for perf in now_fts]
            dates = [datetime.fromtimestamp(p['EffectiveDate']) for p in now_fts]
            fts_data = calculate_fts(prof_fts, dates)

            dates = [datetime.fromtimestamp(p['EffectiveDate']) for p in fts]
            prof_array = [perf["NetReturn"] for perf in fts]
            fts = Series(data=prof_array, index=dates, name=port_folio.name)

            T = len(fts)
            referenceData = await report_dao.findReferenceData('Risk Free Rate')
            if referenceData:
                rf = float(referenceData.data) * 0.01
            else:
                rf = 0

            stats_all = BasicStats(fts, risk_free=rf, folio_name=port_folio.name)
            roll_windows = windows[stats_all.freq[0]]
            roll_results = []
            ratio_items = {"Cumulative Return": [],
                           "Period volatility": {"volatility": "", "day_7_volatility":""},
                           "Max Drawdown": {"max_drawdown": "", "day_7_drawdown": ""},
                           "entire_history": "", "day_7_history":""}

            resultsAll = helper.help(stats_all)
            result_dict = dict(resultsAll)
            ratio_items["entire_history"] = fts_data["entire_history"]  if fts_data else 0.0
            ratio_items["day_7_history"] = fts_data["day_7_history"] if fts_data else 0.0
            ratio_items["Period volatility"]["volatility"] = fts_data["total_volatility"]  if fts_data else 0.0
            ratio_items["Max Drawdown"]["max_drawdown"] = fts_data["total_max_drawdown"]  if fts_data else 0.0
            ratio_items["Cumulative Return"].append(result_dict.get(_("Cumulative Return",lang), ""))
            for index, w in enumerate(roll_windows):
                if T >= w:
                    roll_fts = fts[-1 * w:]
                    ratio_data = helper.help(BasicStats(roll_fts, risk_free=rf))
                    ratio_dict = dict(ratio_data)
                    val = ratio_dict.get(_("Cumulative Return",lang), "")
                    ratio_items["Cumulative Return"].append(val)
                    if index == 0:
                        ratio_items["Max Drawdown"]["day_7_drawdown"] = fts_data["week_max_drawdown"]  if fts_data else 0.0
                        ratio_items["Period volatility"]["day_7_volatility"] = fts_data["week_volatility"]  if fts_data else 0.0
                    roll_results.append([w, ratio_data])
            await folios_dao.updateFolioHistory(port_folio.id, ratio_items)

            reportData = {
                "ResultsAll": resultsAll,
                "RollResults": roll_results,
                "Coin": {"Name": port_folio.name}
            }
            params = "ratios_%s"%lang
            await db.set_cache(port_folio.id, "portfolio", params, data=reportData, modify_at=port_folio.modify_at)
        else:
            roll_results = []
            ratio_items = {"Cumulative Return": [],
                           "Period volatility": {"volatility": ""},
                           "Max Drawdown": {"max_drawdown": "", "day_7_drawdown": ""}}

            resultsAll = helper.init_help()
            result_dict = dict(resultsAll)
            
            ratio_items["Period volatility"]["volatility"] = result_dict.get("% Volatility", "")
            ratio_items["Max Drawdown"]["max_drawdown"] = result_dict.get("Max Drawdown", "")
            ratio_items["Cumulative Return"].append(result_dict.get("Cumulative Return", ""))
            await folios_dao.updateFolioHistory(port_folio.id, ratio_items)

            reportData = {
                "ResultsAll": resultsAll,
                "RollResults": roll_results,
                "Coin": {"Name": port_folio.name}
            }

    except Exception as e:
        errMsg = getErrorMsg()
        error("portfolio_ratios exception is: %s, errMsg: %s"%(str(e), str(errMsg)))
        reportData = {}

    return reportData


class BenchmarkAnalysis:

    def __init__(self, item, bench_ticker=None, modify_at=None):

        self.item = item
        self.db = Connection.getInstance()
        self.bench_ticker = bench_ticker
        self.modify_at = modify_at

    async def analysis(self):

        if not self.bench_ticker:
            self.benchmark_ticker = "^bitcoin"
        else:
            self.benchmark_ticker = self.bench_ticker
        self.benchmark = await self.db.get_risk_factor(self.benchmark_ticker, self.modify_at)
        if self.item:
            performance_data = self.item.folio_ts
        else:
            performance_data = Series()

        self.item_ts = performance_data
        self.bench_ts = self.benchmark.Performance if self.benchmark else Series()
        self.reg_capm = RegressionAnalysis(self.item_ts, self.bench_ts)
        self.bench_ts2 = self.bench_ts ** 2
        self.bench_ts2.name = 'TMY'
        self.reg_tmy = RegressionAnalysis(self.item_ts, [self.bench_ts, self.bench_ts2])
        self.corr_analysis = CorrelationAnalysis(self.item_ts, self.bench_ts)
        self.captures = CaptureRatios(self.item_ts, self.bench_ts)
        self.coin_stats = BasicStats(self.item_ts)
        self.bench_stats = BasicStats(self.bench_ts)

class BasicReport:

    def __init__(self, item_id, start_at=None, isPortFolio=True):
        self.db = Connection.getInstance()
        self.item_id = item_id
        self.start_at = start_at
        self.isPortFolio = isPortFolio

    async def analysis(self):

        if self.isPortFolio:
            self.item = await self.db.get_portfolio(self.item_id, modify_num=180)
            if self.item:
                performance_data = self.item.folio_ts
            else:
                performance_data = Series()
            modify_at = toPreTimestamp(self.start_at)
        else:
            self.item = await self.db.get_coin(self.item_id)
            if self.item:
                performance_data = self.item.Performance
            else:
                performance_data = Series()
            modify_at = None

        self.perf = CoinPerformance(performance_data).series
        self.values = self.perf.values
        await self.populate_time_series(modify_at)
        self.get_histogram()
        self.calculate_vami_chart()
        self.calculate_stats()

    def get_histogram(self):
        """
            Calculate Histogram
        """
        cnt, bins = histogram(self.values, bins='sqrt')
        self.histogram_data = list([toDecimal(b), int(c)] for b, c in zip(bins[1:], cnt))

    def calculate_stats(self):
        self.basicStats = BasicStats(self.perf)
        n = len(self.data_frame.columns)
        self.n_benchmarks = n - 1
        self.mddser = self.basicStats.mdd_ser
        self.mdd_dates = self.mddser.index
        self.mdds = self.mddser.values
        styleTime = (datetime.utcfromtimestamp(int(self.start_at))) if self.start_at else ""

        def day_date(date_str):
            if len(str(date_str)) == 1:
                return "0%s"%str(date_str)
            else:
                return str(date_str)

        def compare_date(d):
            return (int(str(d.year) + day_date(d.month) + day_date(d.day)) >= int(
                str(styleTime.year) + day_date(styleTime.month) + day_date(styleTime.day))) if styleTime else False

        if n > 1:
            bench_values = self.data_frame[self.data_frame.columns[1]].values
            bench_series = Series(data=bench_values, index=self.data_frame.index)
            self.bench_stats = BasicStats(bench_series)
            self.bench_mdd = self.bench_stats.mdd_ser
            self.mdd_res = sorted([(d, m, b) for d, m, b in zip(self.mdd_dates, self.mdds, self.bench_mdd)])
            self.mdd_reses = [[{"year": str(d.year), "month": day_date(d.month), "day": day_date(d.day)}, m, b, compare_date(d)] for d, m, b in self.mdd_res]
        else:
            self.mdd_res = sorted([(d, m) for d, m in zip(self.mdd_dates, self.mdds)])
            self.mdd_reses = [[{"year": str(d.year), "month": day_date(d.month), "day": day_date(d.day)}, toDecimal(m), compare_date(d)] for d, m in self.mdd_res]

        self.var = toDecimal(self.basicStats.var)

    async def populate_time_series(self, start_at=None):
        """
            Get a set of common time series based on item and benchmarks (if any)
        """
        self.all_series = [self.perf]
        if 'Benchmarks' in self.item.__dict__:
            self.benchmarks = self.item.Benchmarks
            for ticker in self.item.Benchmarks:
                bench = await self.db.get_risk_factor(ticker, start_at)
                if bench:
                    if len(bench.Performance) > 0:
                        self.all_series.append(bench.Performance)
            self.data_frame = align_series(self.all_series)
        else:
            self.benchmarks = []
            self.n_benchmarks = 0
            self.data_frame = DataFrame(self.perf)

    def calculate_vami_chart(self):
        self.cum_values = (self.data_frame + 1).cumprod().values
        data = []
        T = len(self.data_frame)
        for t in range(T):
            arr = []
            cum_list = self.cum_values[t, :].tolist()
            cum_list = [toDecimal(cu) for cu in cum_list]
            for cum in cum_list:
                arr.append(cum)
            data.append(arr)
        dates = self.data_frame.index

        pydate_array = dates.to_pydatetime()
        date_only_array = np.vectorize(lambda s: s.strftime('%Y-%m-%d'))(pydate_array)
        date_only_series = pd.Series(date_only_array)
        dates = date_only_series.to_dict().values()

        dates = [{"year": date.split("-")[0], "month": date.split("-")[1], "day": date.split("-")[2]} for date in dates]
        self.vami_cols = self.data_frame.columns.values.tolist()
        self.vami_data = list(zip(dates, data))

        def day_date(date_str):
            if len(str(date_str)) == 1:
                return "0%s"%str(date_str)
            else:
                return str(date_str)

        styleTime = (datetime.utcfromtimestamp(int(self.start_at))) if self.start_at else ""
        if styleTime:
            month = day_date(styleTime.month)
            day = day_date(styleTime.day)
            styleDate = str(styleTime.year) + month + day
        else:
            styleDate = ""

        info_data = {"isStart":True,"start_val":None}

        def compare_date(d, infoData):
            try:
                time_str = str(d[0]["year"]) + str(d[0]["month"]) + str(d[0]["day"])
                val = (int(time_str) >= int(styleDate)) if styleDate else False
                if val and infoData["isStart"]:
                    infoData["isStart"] = False
                    infoData["start_val"] = d[1]
                val = True if int(time_str) == int(styleDate) else val
                compare_data = [d[0], d[1], val]
            except:
                compare_data = d
            return compare_data

        self.vami_data = [compare_date(list(item), info_data) for item in self.vami_data]
        if info_data["start_val"] and float(info_data["start_val"][0]):
            self.vami_data_rate = [[item[0], [toDecimal(float(item[1][0])/float(info_data["start_val"][0]), style="0.000")], item[2]] for item in self.vami_data]
        else:
            self.vami_data_rate = self.vami_data

        values = [toDecimal(val) for val in self.values]
        self.hist_chart_items = list(zip(dates, values))
        self.hist_chart_data = [compare_date(list(item), info_data) for item in self.hist_chart_items]


class StyleAnalysis:

    def __init__(self, item_id, tickers, isPortfolio=True, started_at=""):
        self.db = Connection.getInstance()
        self.item_id = item_id
        self.tickers = tickers
        self.started_at = started_at
        self.isPortfolio = isPortfolio

    async def analysis(self):
        if self.isPortfolio:
            self.item = await self.db.get_portfolio(self.item_id, modify_num=30)
            if self.item:
                performance_data = self.item.folio_ts
                modify_at = self.item.modify_at
            else:
                performance_data = Series()
                modify_at = None
        else:
            self.item = await self.db.get_coin(self.item_id)
            modify_at = None
            if self.item:
                performance_data = self.item.Performance
            else:
                performance_data = Series()

        self.risk_factors = await self.db.get_risk_factors(self.tickers, modify_at, self.isPortfolio)
        self.factor_ts = [r.Performance for r in self.risk_factors]
        self.coin_ts = performance_data
        self.reg_analysis = RegressionAnalysis(self.coin_ts, self.factor_ts)
        self.factor_names = [r.Name for r in self.risk_factors]
        self.factor_names.append("Unexplained")
        self.common_data = self.reg_analysis.common_data
        self.N = len(self.factor_names)
        self.T = len(self.common_data)
        self.rolling_reg = []
        self.IsPortfolio = self.isPortfolio
        if self.T >= 12:
            window = 12
            if self.T >= 36:
                window = 24
            dates = self.common_data.index

            def day_date(date_str):
                if len(str(date_str)) == 1:
                    return "0%s" % str(date_str)
                else:
                    return str(date_str)

            styleTime = (datetime.utcfromtimestamp(int(self.started_at))) if self.started_at else ""
            if styleTime:
                month = day_date(styleTime.month)
                day = day_date(styleTime.day)
                styleDate = str(styleTime.year) + month + day
            else:
                styleDate = ""

            def compare_date(d):
                return (int(str(d["year"]) + str(d["month"]) + str(d["day"])) >= int(styleDate)) if styleDate else False

            for t0 in range(window, self.T):
                idx = range(t0 - window, t0)
                rolldates = dates[idx]
                ser = lambda c: Series(data=self.common_data.iloc[idx, c], index=rolldates)
                y_ts = ser(0)
                x_ts = [ser(c + 1) for c in range(self.N - 1)]
                rollreg = RegressionAnalysis(y_ts, x_ts)
                rollreg_dict = {"betas":rollreg.betas, "crisk":[toDecimal(crisk) for crisk in rollreg.crisk]}
                d = rolldates[-1]
                rolldate = {"year": str(d.year), "month": day_date(d.month), "day": day_date(d.day)}
                self.rolling_reg.append([rolldate, rollreg_dict, compare_date(rolldate)])
            self.rolling_window = window
            self.RollingT = len(self.rolling_reg)
