import csv
import os
import json


def getErc1155TxnsFromSpreadsheet(wallet, data_path):
    # assumption: a single data file (csv) will be placed under %data_path%/ERC1155
    path = data_path + "ERC1155/"
    for file in os.listdir(path):
        if file.endswith(".csv") and wallet.lower() in file.lower():
            with open(path + file, "r") as f:
                txns = list(csv.DictReader(f))

            txns_standard = []
            for t in txns:
                txns_standard.append({
                    'hash': t['Txhash'],
                    'timeStamp': t['UnixTimestamp'],
                    'from': t['From'],
                    'to': t['To'],
                    'contractAddress': t['ContractAddress'],
                    'tokenId': t['TokenId'],
                    'tokenName': t['TokenName'],
                    'tokenSymbol': t['TokenSymbol'],
                    'note': t['PrivateNote']
                })

            return txns_standard

    print("Cannot find ERC-1155 data file for ", wallet)
    return []


def getCoinbaseTxnsFromSpreadsheet(data_path):
    # assumption: a single data file (csv) will be placed under %data_path%/Coinbase,
    #   Spreadsheet is downloaded from transaction report
    path = data_path + "Coinbase/"
    for file_name in os.listdir(path):
        if file_name.endswith(".csv"):
            with open(path + file_name, "r") as file:
                header_line = 0
                for line in file:
                    if line.startswith("Timestamp,"):
                        break
                    else:
                        header_line += 1

            with open(path + file_name, "r") as file:
                for i in range(header_line):
                    next(file)

                return list(csv.DictReader(file))

    print("Cannot find any Coinbase data file")
    return []


def cacheTransactions(transaction_data, data_cache_f):
    with open(data_cache_f, 'w') as f:
        json.dump({'data': transaction_data}, f)


def readTransactionsCache(data_cache_f):
    with open(data_cache_f) as f:
        json_data = json.load(f)
        return json_data['data']
