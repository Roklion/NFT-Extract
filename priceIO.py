from pycoingecko import CoinGeckoAPI
from datetime import *
from ratelimit import limits, sleep_and_retry

ONE_MINUTE = 60
ONE_SECOND = 1
MAX_CALLS_PER_MINUTE_CG = 40    # API limit is 50 calls/min
MAX_CALLS_PER_SECOND_CG = 7     # API limit is 8 calls/min

cg = CoinGeckoAPI()
token_data_cache = {}


@sleep_and_retry
@limits(calls=MAX_CALLS_PER_MINUTE_CG, period=ONE_MINUTE)
def _getCoinHistoryByIdCoinGecko(from_token, date_str):
    global cg
    return cg.get_coin_history_by_id(from_token.lower(), date_str)


def _getTokenHistData(from_token, to, date_str):
    global token_data_cache

    from_token = from_token.lower()
    to = to.lower()

    if from_token in token_data_cache:
        if to in token_data_cache[from_token]:
            if date_str in token_data_cache[from_token][to]:
                return token_data_cache[from_token][to][date_str]

    price_data = _getCoinHistoryByIdCoinGecko(from_token, date_str)
    price = price_data['market_data']['current_price'][to]

    # cache it
    token_data_cache.setdefault(from_token, {to: {}})
    token_data_cache[from_token][to][date_str] = price

    return price


def getTokenHistData(from_token, to, timestamp):
    datetime_obj = datetime.fromtimestamp(int(timestamp))
    date_str = "%02d-%02d-%4d" % (datetime_obj.day, datetime_obj.month, datetime_obj.year)

    return _getTokenHistData(from_token, to, date_str)
