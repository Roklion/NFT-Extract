from constants import *
import priceIO
from web3 import Web3
from datetime import *


def groupByNormalTxns(txn: dict,
                      txns_internal: list,
                      txns_erc20: list,
                      txns_erc721: list,
                      txns_erc1155: list) -> dict:
    txn_hash = txn['hash']
    return ({
        'txn_hash': txn_hash,
        'txn_normal': txn,
        'txn_internal': [t for t in txns_internal if t['hash'] == txn_hash],
        'txn_erc20': [t for t in txns_erc20 if t['hash'] == txn_hash],
        'txn_erc721': [t for t in txns_erc721 if t['hash'] == txn_hash],
        'txn_erc1155': [t for t in txns_erc1155 if t['Txhash'] == txn_hash]
    })


def _processErc20Txns(txns_erc20: list) -> dict:
    erc20_summary = {}
    for txn in txns_erc20:
        if txn['tokenSymbol'] not in erc20_summary:
            erc20_summary[txn['tokenSymbol']] = []

        erc20_summary[txn['tokenSymbol']].append({
            'value': float(txn['value']) / pow(10, int(txn['tokenDecimal'])),
            'contract': txn['contractAddress'],
            'name': txn['tokenName'],
            'symbol': txn['tokenSymbol'],
            'from': txn['from'],
            'to': txn['to']
        })

    return erc20_summary


def _processErc721Txns(txns_erc721: list) -> dict:
    erc721_summary = {}
    for txn in txns_erc721:
        token_id = txn['tokenSymbol'] + txn['tokenID']
        if token_id not in erc721_summary:
            erc721_summary[token_id] = []

        erc721_summary[token_id].append({
            'value': 1.0,
            'contract': txn['contractAddress'],
            'name': txn['tokenName'],
            'symbol': txn['tokenSymbol'],
            'id': txn['tokenID'],
            'from': txn['from'],
            'to': txn['to']
        })

    return erc721_summary


def _processErc1155Txns(txns_erc1155: list) -> dict:
    erc1155_summary = {}
    for txn in txns_erc1155:
        if txn['TokenSymbol'] not in erc1155_summary:
            erc1155_summary[txn['TokenSymbol']] = []

        erc1155_summary[txn['TokenSymbol']].append({
            'value': float(txn['TokenName']),
            'contract': txn['ContractAddress'],
            'name': txn['TokenSymbol'],
            'symbol': txn['TokenSymbol'],
            'id': txn['TokenId'],
            'from': txn['From'],
            'to': txn['To']
        })

    return erc1155_summary


def enrichTxn(txn_grouped: dict) -> dict:
    txn_grouped_enriched = txn_grouped
    txn_normal = txn_grouped['txn_normal']

    # Process gas and ETH
    gas_amount = float(Web3.fromWei(int(txn_normal['gasPrice']) * int(txn_normal['gasUsed']), 'ether'))
    eth_amount = float(Web3.fromWei(int(txn_normal['value']), 'ether'))
    timestamp = int(txn_normal['timeStamp'])
    txn_summary = {
        'gas': {
            'amount': gas_amount,
            'value_usd': gas_amount * priceIO.getTokenHistData("ethereum", "USD", timestamp)
        },
        'ETH': {
            'amount': eth_amount,
            'value_usd': eth_amount * priceIO.getTokenHistData("ethereum", "USD", timestamp),
            'from': txn_normal['from'],
            'to': txn_normal['to']
        },
        'timestamp': timestamp,
        'time': datetime.utcfromtimestamp(timestamp)
    }
    txn_grouped_enriched.update(txn_summary)

    # Process ERC-20 tokens in transaction
    erc20_summary = _processErc20Txns(txn_grouped['txn_erc20'])
    assert not dict(txn_grouped_enriched.items() & erc20_summary.items())  # make sure no overlap
    txn_grouped_enriched.update(erc20_summary)

    # Process ERC-721 tokens in transaction
    erc721_summary = _processErc721Txns(txn_grouped['txn_erc721'])
    assert not dict(txn_grouped_enriched.items() & erc721_summary.items())  # make sure no overlap
    txn_grouped_enriched.update(erc721_summary)

    erc1155_summary = _processErc1155Txns(txn_grouped['txn_erc1155'])
    assert not dict(txn_grouped_enriched.items() & erc1155_summary.items())  # make sure no overlap
    txn_grouped_enriched.update(erc1155_summary)

    return txn_grouped_enriched


def _compareTimestamp(txn_a, txn_b):
    return txn_a['timestamp'] < txn_b['timestamp']


def _describeEtherscanTxn(txn, my_wallets):
    eth_data = txn['ETH']
    gas_data = txn['gas']
    addr_from = eth_data['from'].lower()
    addr_to = eth_data['to'].lower()
    if addr_from in my_wallets and addr_to in my_wallets:
        txn_type = 'transfer'
        describe_str = 'Transfer {:.5f}E (worth ${:.2f}) from 0x...{} to 0x...{} ' \
                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'], eth_data['value_usd'],
                                                                 addr_from[-5:], addr_to[-5:],
                                                                 gas_data['amount'], gas_data['value_usd'])
    elif addr_from in COINBASE_WALLETS and addr_to in my_wallets:
        txn_type = 'transfer_from_coinbase'
        describe_str = 'Transfer {:.5f}E (worth ${:.2f}) from Coinbase to 0x...{} ' \
                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'], eth_data['value_usd'],
                                                                 addr_to[-5:],
                                                                 gas_data['amount'], gas_data['value_usd'])
    elif addr_to in COINBASE_WALLETS:
        txn_type = 'transfer_to_coinbase'
        describe_str = 'Transfer {:.5f}E (worth ${:.2f}) from 0x...{} to Coinbase ' \
                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'], eth_data['value_usd'],
                                                                 addr_from[-5:],
                                                                 gas_data['amount'], gas_data['value_usd'])
    elif addr_from in my_wallets:
        txn_type = 'buy_nft'
        describe_str = 'Buy NFT for {:.5f}E (worth ${:.2f}) for 0x...{} ' \
                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'], eth_data['value_usd'],
                                                                 addr_from[-5:],
                                                                 gas_data['amount'], gas_data['value_usd'])
    elif addr_to in my_wallets:
        txn_type = 'sell_nft'
        describe_str = 'Sell NFT for {:.5f}E (worth ${:.2f}) for 0x...{} ' \
                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'], eth_data['value_usd'],
                                                                 addr_to[-5:],
                                                                 gas_data['amount'], gas_data['value_usd'])

    else:
        txn_type = 'unknown'
        describe_str = 'Transfer {:.5f}E (worth ${:.2f}) from 0x...{} to 0x...{} ' \
                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'], eth_data['value_usd'],
                                                                 addr_from[-5:], addr_to[-5:],
                                                                 gas_data['amount'], gas_data['value_usd'])

        raise Exception('Unknown transaction type {}\n{}'.format(txn_type, describe_str))

    return {
        'type': txn_type,
        'ETH': eth_data,
        'gas': gas_data,
        'description': describe_str,
        'timestamp': txn['timestamp'],
        'id': txn['txn_hash']
    }


def _describeCoinbaseTxn(txn, asset, my_wallets):
    if txn['Asset'].lower() == asset.lower():
        is_transfer = is_gift = False
        addr_target = ""

        txn_type_raw = txn['Transaction Type'].lower()
        if txn_type_raw != 'send' and txn_type_raw != 'buy':
            raise Exception('Unknown transaction type from coinbase {}'.format(txn_type_raw))

        if txn_type_raw == 'send':
            is_transfer = True
            addr_target = txn['Notes'].split()[-1].lower()

            if addr_target not in my_wallets:
                is_gift = True
                txn_type = 'gift'
            else:
                txn_type = 'transfer_by_coinbase'
        else:
            txn_type = txn_type_raw
            addr_target = ''

        eth_data = {
            'amount': float(txn['Quantity Transacted']),
            'value_usd': float(txn['Quantity Transacted']) * float(txn['Spot Price at Transaction']),
            'to': addr_target
        }
        gas_data = {
            'value_usd': float(txn['Fees']) if not is_transfer else 0
        }

        if is_gift:
            describe_str = 'Gift {:.5f}E (worth ${:.2f}) ' \
                           'from Coinbase to 0x...{}'.format(eth_data['amount'], eth_data['value_usd'],
                                                             addr_target[-5:])
        elif is_transfer:
            describe_str = 'Transfer {:.5f}E (worth ${:.2f}) ' \
                           'from Coinbase to 0x...{}'.format(eth_data['amount'], eth_data['value_usd'],
                                                             addr_target[-5:])
        else:
            describe_str = 'Buy {:.5f}E for ${:.2f} with ${:.2f} fee'.format(eth_data['amount'], eth_data['value_usd'],
                                                                             gas_data['value_usd'])

        return {
            'type': txn_type,
            'ETH': eth_data,
            'gas': gas_data,
            'description': describe_str,
            'timestamp': txn['timestamp'],
            'id': ''
        }
    else:
        return {}


def describeEthTxns(coinbase_txns, etherscan_txns, my_wallets):
    def sortByTimestamp(x):
        return x['timestamp']

    coinbase_txns.sort(key=sortByTimestamp)
    etherscan_txns.sort(key=sortByTimestamp)
    eth_descriptions = []

    i = j = 0
    max_i = len(coinbase_txns) - 1
    max_j = len(etherscan_txns) - 1
    while i <= max_i or j <= max_j:
        # if exhausted etherscan txns
        if j > max_j:
            eth_descriptions.append(_describeCoinbaseTxn(coinbase_txns[i], "ETH", my_wallets))
            i += 1
        # if exhausted coinbase txns
        elif i > max_i:
            eth_descriptions.append(_describeEtherscanTxn(etherscan_txns[j], my_wallets))
            j += 1
        # if coinbase txn timestamp earlier (smaller)
        elif _compareTimestamp(coinbase_txns[i], etherscan_txns[j]):
            eth_descriptions.append(_describeCoinbaseTxn(coinbase_txns[i], "ETH", my_wallets))
            i += 1
        # else - etherscan txn timestamp earlier (smaller)
        else:
            eth_descriptions.append(_describeEtherscanTxn(etherscan_txns[j], my_wallets))
            j += 1

    # remove empty transactions, not relevant to ETH
    eth_descriptions = [x for x in eth_descriptions if x]
    return eth_descriptions
