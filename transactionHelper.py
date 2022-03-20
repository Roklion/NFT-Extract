from web3 import Web3
from datetime import *
import priceIO


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


