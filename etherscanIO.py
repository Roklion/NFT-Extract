from etherscan import Etherscan
from constants import *
from ratelimit import limits, sleep_and_retry


def initialize(api_key):
    # initialize API interface
    global eth
    eth = Etherscan(api_key)


# Conservative rate limit to avoid API errors
@sleep_and_retry
@limits(calls=MAX_CALLS_PER_SECOND_ETHERSCAN, period=ONE_SECOND)
def getContract(address):
    return eth.get_contract_source_code(address)[0]
