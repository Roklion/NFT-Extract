# Known platform wallets/addresses
COINBASE_WALLETS = [
    "0xddfAbCdc4D8FfC6d5beaf154f18B778f892A0740",
    "0x3cD751E6b0078Be393132286c442345e5DC49699",
    "0xb5d85CBf7cB3EE0D56b3bB207D5Fc4B82f43F511",
    "0xeB2629a2734e272Bcc07BDA959863f316F4bD4Cf"
]
RONIN_BRIDGE = [
    "0x1a2a1c938ce3ec39b6d47113c7955baa9dd454f2"
]
POLYGON_BRIDGE = [
    "0xa0c68c638235ee32657e8f720a23cec1bfc77c77"
]
WETH_CONTRACT = [
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
]
BURN_ADDRESSES = [
    "0xeea89c8843e8beb56e411bb4cac6dbc2d937ee1d",
    "0x000000000000000000000000000000000000dEaD"
]
IGNORE_ADDRESS = [
    "0x82dfdb2ec1aa6003ed4acba663403d7c2127ff67",   # Fake/Phishing
]

COINBASE_WALLETS = [x.lower() for x in COINBASE_WALLETS]
RONIN_BRIDGE = [x.lower() for x in RONIN_BRIDGE]
POLYGON_BRIDGE = [x.lower() for x in POLYGON_BRIDGE]
WETH_CONTRACT = [x.lower() for x in WETH_CONTRACT]
BURN_ADDRESSES = [x.lower() for x in BURN_ADDRESSES]
IGNORE_ADDRESS = [x.lower() for x in IGNORE_ADDRESS]

# Cost Method
COST_METHOD_HIFO = 'HIFO'


# Sorting function
def SORT_FUNC_BY_PRICE(x):
    return x['unit_price_usd']


# For API rate limit
ONE_MINUTE = 60
ONE_SECOND = 1
MAX_CALLS_PER_MINUTE_CG = 25  # API limit is 50 calls/min
MAX_CALLS_PER_SECOND_CG = 4  # API limit is 8 calls/min
MAX_CALLS_PER_SECOND_ETHERSCAN = 4  # API limit is 5 calls/sec


# Files
TRANSACTION_DATA_CACHE_F = "transaction_datadump.json"
