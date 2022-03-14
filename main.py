import etherscanIO as EtherIO
import transactionHelper as txnHelper
import os

walletAddr = "0x3a327EaaFD07A8F4f5001481943E69D8c618e2FB"
dataPath = os.path.curdir + "/data"
print("Hello World! -Roklion\n")
print("Wallet Address is", walletAddr)

EtherIO.initialize()
txns_normal = EtherIO.getTxns(walletAddr)
txns_internal = EtherIO.getInternalTxns(walletAddr)
txns_erc20 = EtherIO.getErc20Txns(walletAddr)
txns_erc721 = EtherIO.getErc721Txns(walletAddr)
txns_erc1155 = EtherIO.getErc1155Txns(walletAddr, dataPath)

txn_groups = []
for txn in txns_normal:
    txn_grouped = txnHelper.groupByNormalTxns(txn, txns_internal, txns_erc20, txns_erc721, txns_erc1155)
    txn_grouped_enriched = txnHelper.enrichTxn(txn_grouped)
    txn_groups.append(txn_grouped_enriched)

print(len(txns_normal), " transactions")
print(len(txns_internal), " internal transactions")
print(len(txns_erc20), " ERC-20 transactions")
print(len(txns_erc721), " ERC-721 transactions")
print(len(txns_erc1155), " ERC-1155 transactions")
