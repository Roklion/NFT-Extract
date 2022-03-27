import etherscanIO as etherscan
import fileIO
import csv
import os
import json

def getTxns(wallet):
    # Etherscan API for transactions
    try:
        return etherscan.eth.get_normal_txs_by_address(wallet, 0, 99999999, "asc")
    except:
        print("Cannot retrieve transasctions for ", wallet)
        return []

def getInternalTxns(wallet):
    # Etherscan API for transactions
    try:
        return etherscan.eth.get_internal_txs_by_address(wallet, 0, 99999999, "asc")
    except:
        print("Cannot retrieve internal transactions for ", wallet)
        return []

def getErc20Txns(wallet):
    # Etherscan API for transactions
    try:
        return etherscan.eth.get_erc20_token_transfer_events_by_address(wallet, 0, 99999999, "asc")
    except:
        print("Cannot retrieve ERC-20 transactions for ", wallet)
        return []

def getErc721Txns(wallet):
    # Etherscan API for transactions
    try:
        return etherscan.eth.get_erc721_token_transfer_events_by_address(wallet, 0, 99999999, "asc")
    except:
        print("Cannot retrieve ERC-721 transactions for ", wallet)
        return []

def getErc1155Txns(wallet, data_path):
    # Etherscan API for transactions not yet available, retrieve from spreadsheet
    return fileIO.getErc1155TxnsFromSpreadsheet(wallet, data_path)
