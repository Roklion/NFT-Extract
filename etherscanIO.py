from etherscan import Etherscan


def initialize(api_key):
    # initialize API interface
    global eth
    eth = Etherscan(api_key)


def getContract(address):
    return eth.get_contract_source_code(address)[0]
