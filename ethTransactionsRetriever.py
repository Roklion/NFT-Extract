from etherscan import Etherscan
import fileIO
import csv
import os

def initialize(api_key):
    global eth
    eth = Etherscan(api_key)

def getTxns(wallet):
    try:
        return eth.get_normal_txs_by_address(wallet, 0, 99999999, "asc")
    except:
        print("Cannot retrieve transasctions for ", wallet)
        return []

def getInternalTxns(wallet):
    try:
        return eth.get_internal_txs_by_address(wallet, 0, 99999999, "asc")
    except:
        print("Cannot retrieve internal transactions for ", wallet)
        return []

def getErc20Txns(wallet):
    try:
        return eth.get_erc20_token_transfer_events_by_address(wallet, 0, 99999999, "asc")
    except:
        print("Cannot retrieve ERC-20 transactions for ", wallet)
        return []

def getErc721Txns(wallet):
    try:
        return eth.get_erc721_token_transfer_events_by_address(wallet, 0, 99999999, "asc")
    except:
        print("Cannot retrieve ERC-721 transactions for ", wallet)
        return []

def getErc1155Txns(wallet, data_path):
    return fileIO.getErc1155TxnsFromSpreadsheet(wallet, data_path)
