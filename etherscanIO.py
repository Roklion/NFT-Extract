from etherscan import Etherscan
import csv
import os

def initialize(api_key):
    global eth
    eth = Etherscan(api_key)

def getTxns(wallet):
    try:
        return(eth.get_normal_txs_by_address(wallet, 0, 99999999, "asc"))
    except:
        print("Cannot retrieve transasctions for ", wallet)
        return([])

def getInternalTxns(wallet):
    try:
        return(eth.get_internal_txs_by_address(wallet, 0, 99999999, "asc"))
    except:
        print("Cannot retrieve internal transactions for ", wallet)
        return([])

def getErc20Txns(wallet):
    try:
        return(eth.get_erc20_token_transfer_events_by_address(wallet, 0, 99999999, "asc"))
    except:
        print("Cannot retrieve ERC-20 transactions for ", wallet)
        return([])

def getErc721Txns(wallet):
    try:
        return(eth.get_erc721_token_transfer_events_by_address(wallet, 0, 99999999, "asc"))
    except:
        print("Cannot retrieve ERC-721 transactions for ", wallet)
        return([])

def getErc1155Txns(wallet, dataPath):
    return(_getErc1155TxnsFromSpreadsheet(wallet, dataPath))

def _getErc1155TxnsFromSpreadsheet(wallet, dataPath):
    # assumption: a single data file (csv) will be placed under %datapath%/ERC1155,
    #       and the file name should contains wallet address
    path = dataPath + "/ERC1155/"
    for file in os.listdir(path):
        if file.endswith(".csv") and wallet.lower() in file.lower():
            with open(path + file, "r") as f:
                return(list(csv.DictReader(f)))
                #return([{k: v for k, v in row.items()}
                #     for row in csv.DictReader(f)])

    print("Cannot find ERC-1155 data file for ", wallet)
    return([])