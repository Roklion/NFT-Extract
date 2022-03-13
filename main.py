import etherscanIO as EtherIO
import os

walletAddr = "0x3a327EaaFD07A8F4f5001481943E69D8c618e2FB"
dataPath = os.path.curdir + "/data"
print("Hello World! -Roklion\n")
print("Wallet Address is", walletAddr)

EtherIO.initialize()
txns_normal = EtherIO.get_txns(walletAddr)
txns_internal = EtherIO.get_internal_txns(walletAddr)
txns_erc20 = EtherIO.get_erc20_txns(walletAddr)
txns_erc721 = EtherIO.get_erc721_txns(walletAddr)
txns_erc1155 = EtherIO.get_erc1155_txns_spreadsheet(walletAddr, dataPath)

print(len(txns_normal), " transactions")
print(len(txns_internal), " internal transactions")
print(len(txns_erc20), " ERC-20 transactions")
print(len(txns_erc721), " ERC-721 transactions")