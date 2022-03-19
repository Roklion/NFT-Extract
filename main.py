import etherscanIO as EtherIO
import transactionHelper as txnHelper
import json
import os
from datetime import *


start_date = "2021-01-01"
end_date = "2021-12-31"
with open(os.path.curdir + "/config/config.json") as json_data_file:
    config = json.load(json_data_file)

dataPath = os.path.curdir + config['dataFilePath']
EtherIO.initialize(config['etherscanApiKey'])
coinbase_txn = txnHelper.getCoinbaseTxns(dataPath)

txn_groups = []
txn_count = 0

if start_date:
    start_timestamp = datetime.timestamp(datetime.strptime(start_date, "%Y-%m-%d"))
else:
    start_timestamp = 0.0
if end_date:
    end_timestamp = datetime.timestamp(datetime.strptime(end_date, "%Y-%m-%d"))
else:
    end_timestamp = datetime.timestamp(datetime.now())

for walletAddr in config['ethWallets']:
    print("Wallet Address is", walletAddr)

    txns_normal = EtherIO.getTxns(walletAddr)
    txns_internal = EtherIO.getInternalTxns(walletAddr)
    txns_erc20 = EtherIO.getErc20Txns(walletAddr)
    txns_erc721 = EtherIO.getErc721Txns(walletAddr)
    txns_erc1155 = EtherIO.getErc1155Txns(walletAddr, dataPath)

    for txn in txns_normal:
        time_stamp = float(txn['timeStamp'])
        date = datetime.fromtimestamp(time_stamp)
        if time_stamp < start_timestamp or time_stamp > end_timestamp:
            continue
        txn_grouped = txnHelper.groupByNormalTxns(txn, txns_internal, txns_erc20, txns_erc721, txns_erc1155)
        txn_grouped_enriched = txnHelper.enrichTxn(txn_grouped)
        txn_groups.append(txn_grouped_enriched)
        txn_count += 1
        print(str(txn_count), " transactions processed ", date)


print(len(txns_normal), " transactions")
print(len(txns_internal), " internal transactions")
print(len(txns_erc20), " ERC-20 transactions")
print(len(txns_erc721), " ERC-721 transactions")
print(len(txns_erc1155), " ERC-1155 transactions")
