import ethTransactionsRetriever as ethTxnsRetriever
import coinbaseRetriever
import transactionHelper as txnHelper
import analyzer
import json
import os
from datetime import *

start_date = "2021-01-01"
end_date = "2021-12-31"
with open(os.path.curdir + "/config/config.json") as json_data_file:
    config = json.load(json_data_file)

data_path = os.path.curdir + config['dataFilePath']
ethTxnsRetriever.initialize(config['etherscanApiKey'])
coinbase_txns = coinbaseRetriever.getCoinbaseTxns(data_path)
my_wallets = [x.lower() for x in config['ethWallets']]

if start_date:
    start_timestamp = datetime.timestamp(datetime.strptime(start_date, "%Y-%m-%d"))
else:
    start_timestamp = 0.0
if end_date:
    end_timestamp = datetime.timestamp(datetime.strptime(end_date, "%Y-%m-%d"))
else:
    end_timestamp = datetime.timestamp(datetime.now())

print("\nTime period for analysis {} to {}".format(start_date, end_date))

txn_groups = []
for wallet_addr in my_wallets:
    print("\nProcessing Etherscan transactions for wallet ", wallet_addr)

    txns_normal = ethTxnsRetriever.getTxns(wallet_addr)
    txns_internal = ethTxnsRetriever.getInternalTxns(wallet_addr)
    txns_erc20 = ethTxnsRetriever.getErc20Txns(wallet_addr)
    txns_erc721 = ethTxnsRetriever.getErc721Txns(wallet_addr)
    txns_erc1155 = ethTxnsRetriever.getErc1155Txns(wallet_addr, data_path)

    txn_count = 0
    for txn in txns_normal:
        time_stamp = float(txn['timeStamp'])
        date = datetime.utcfromtimestamp(time_stamp)
        if time_stamp < start_timestamp or time_stamp > end_timestamp:
            continue
        txn_grouped = txnHelper.groupByNormalTxns(txn, txns_internal, txns_erc20, txns_erc721, txns_erc1155)
        txn_grouped_enriched = txnHelper.enrichTxn(txn_grouped)
        txn_groups.append(txn_grouped_enriched)
        txn_count += 1

    print(str(txn_count), " transactions processed")


try:
    print("\nSummarize ETH transactions")
    eth_txns_summary = txnHelper.describeEthTxns(coinbase_txns, txn_groups, my_wallets)
    print("\nAnalyze ETH")
    eth_balances = analyzer.analyzeEth(eth_txns_summary)
except Exception as e:
    print("Caught an exception ", e)

print("\nTransaction count")

