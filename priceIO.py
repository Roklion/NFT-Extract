from constants import *
from pycoingecko import CoinGeckoAPI
from datetime import *
from ratelimit import limits, sleep_and_retry

cg = CoinGeckoAPI()
token_data_cache = {}


@sleep_and_retry
@limits(calls=MAX_CALLS_PER_MINUTE_CG, period=ONE_MINUTE)
@limits(calls=MAX_CALLS_PER_SECOND_CG, period=ONE_SECOND)
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
    datetime_obj = datetime.fromtimestamp(timestamp)
    date_str = "%02d-%02d-%4d" % (datetime_obj.day, datetime_obj.month, datetime_obj.year)

    return _getTokenHistData(from_token, to, date_str)
