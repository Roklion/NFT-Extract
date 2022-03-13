from etherscan import Etherscan
import csv
import os

def initialize():
    global eth
    eth = Etherscan("4YAQ6IJ938VB3VWEDZB6U3JHTDSNFZM1VG")

def get_txns(wallet):
    try:
        return(eth.get_normal_txs_by_address(wallet, 0, 99999999, "asc"))
    except:
        print("Cannot retrieve transasctions for ", wallet)
        return([])

def get_internal_txns(wallet):
    try:
        return(eth.get_internal_txs_by_address(wallet, 0, 99999999, "asc"))
    except:
        print("Cannot retrieve internal transactions for ", wallet)
        return([])

def get_erc20_txns(wallet):
    try:
        return(eth.get_erc20_token_transfer_events_by_address(wallet, 0, 99999999, "asc"))
    except:
        print("Cannot retrieve ERC-20 transactions for ", wallet)
        return([])

def get_erc721_txns(wallet):
    try:
        return(eth.get_erc721_token_transfer_events_by_address(wallet, 0, 99999999, "asc"))
    except:
        print("Cannot retrieve ERC-721 transactions for ", wallet)
        return([])

def get_erc1155_txns_spreadsheet(wallet, dataPath):
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