import ethTransactionsRetriever as ethTxnsRetriever
import coinbaseRetriever
import fileIO
import transactionHelper as txnHelper
import analyzer
from constants import *
import json
import os
from datetime import *

# Configs and constants
start_date = "2021-01-01"
end_date = "2021-12-31"
with open(os.path.curdir + "/config/config.json") as json_data_file:
    config = json.load(json_data_file)

data_path = os.path.curdir + config['dataFilePath']
data_cache_f = data_path + TRANSACTION_DATA_CACHE_F
ethTxnsRetriever.initialize(config['etherscanApiKey'])

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

# Retrieve transaction data
## Coinbase transactions
print("\nProcessing Coinbase transactions")
coinbase_txns = coinbaseRetriever.getCoinbaseTxns(data_path)

## Etherscan transactions
# optimize speed by checking data cache
if config['forceNewData'] or not os.path.exists(data_path + TRANSACTION_DATA_CACHE_F):
    txn_groups = []
    for wallet_addr in my_wallets:
        print("\nProcessing Etherscan transactions for wallet ", wallet_addr)

        # Retrieve each type of transactions
        txns_normal = ethTxnsRetriever.getTxns(wallet_addr)
        txns_internal = ethTxnsRetriever.getInternalTxns(wallet_addr)
        txns_erc20 = ethTxnsRetriever.getErc20Txns(wallet_addr)
        txns_erc721 = ethTxnsRetriever.getErc721Txns(wallet_addr)
        txns_erc1155 = ethTxnsRetriever.getErc1155Txns(wallet_addr, data_path)

        txn_count = 0
        # Group everything around normal transactions
        for txn in txns_normal:
            # UTC timestamp
            time_stamp = float(txn['timeStamp'])
            date = datetime.utcfromtimestamp(time_stamp)
            if time_stamp < start_timestamp or time_stamp > end_timestamp:
                continue

            # Join transactions into groups around normal transactions
            txn_grouped = txnHelper.groupByNormalTxns(txn, txns_internal, txns_erc20, txns_erc721, txns_erc1155)

            # Extract and enrich transaction group with key information, e.g. gas, ETH amounts, tokens
            txn_grouped_enriched = txnHelper.enrichTxn(txn_grouped)

            txn_groups.append(txn_grouped_enriched)
            txn_count += 1

        print(str(txn_count), " transactions processed")
    # cache new data to file
    fileIO.cacheTransactions(txn_groups, data_cache_f)

# read from data dump instead
else:
    txn_groups = fileIO.readTransactionsCache(data_cache_f)

# Create analytics
try:
    # Normalize coinbase and etherscan transactions
    print("\nSummarize ETH transactions")
    eth_txns_summary = txnHelper.describeEthTxns(coinbase_txns, txn_groups, my_wallets)

    # Create analytic and timeline around ETH transactions
    print("\nAnalyze ETH")
    eth_balances = analyzer.analyzeEth(eth_txns_summary, cost_method=COST_METHOD_HIFO)
except Exception as e:
    print("Caught an exception ", e)

print("\nTransaction count")

