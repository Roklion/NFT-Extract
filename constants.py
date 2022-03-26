# Known platform wallets/addresses
COINBASE_WALLETS = [
    "0xddfAbCdc4D8FfC6d5beaf154f18B778f892A0740",
    "0x3cD751E6b0078Be393132286c442345e5DC49699",
    "0xb5d85CBf7cB3EE0D56b3bB207D5Fc4B82f43F511",
    "0xeB2629a2734e272Bcc07BDA959863f316F4bD4Cf"]
RONIN_BRIDGE = [
    "0x1a2a1c938ce3ec39b6d47113c7955baa9dd454f2"
]
COINBASE_WALLETS = [x.lower() for x in COINBASE_WALLETS]
RONIN_BRIDGE = [x.lower() for x in RONIN_BRIDGE]

# Cost Method
COST_METHOD_HIFO = 'HIFO'

# For API rate limit
ONE_MINUTE = 60
ONE_SECOND = 1
MAX_CALLS_PER_MINUTE_CG = 40  # API limit is 50 calls/min
MAX_CALLS_PER_SECOND_CG = 7  # API limit is 8 calls/min

# Files
TRANSACTION_DATA_CACHE_F = "transaction_datadump.json"
