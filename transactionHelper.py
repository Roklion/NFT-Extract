from etherscanIO import *
from contractHelper import *
from constants import *
import priceIO
from web3 import Web3


def groupByNormalTxns(txn: dict,
                      txns_internal: list,
                      txns_erc20: list,
                      txns_erc721: list,
                      txns_erc1155: list) -> dict:
    # Different type of transactions can be joined by the same transaction hash
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
    erc20_summary = []
    for txn in txns_erc20:
        # tokenDecimal is token precision
        # value represents integer to the most precise digit of the token
        erc20_summary.append({
            'value': float(txn['value']) / pow(10, int(txn['tokenDecimal'])),
            'contract': txn['contractAddress'],
            'name': txn['tokenName'],
            'symbol': txn['tokenSymbol'],
            'from': txn['from'],
            'to': txn['to']
        })

    return {'ERC-20': erc20_summary}


def _processErc721Txns(txns_erc721: list) -> dict:
    erc721_summary = []
    for txn in txns_erc721:
        # ERC-721 token is unique
        erc721_summary.append({
            'value': 1.0,
            'contract': txn['contractAddress'],
            'name': txn['tokenName'],
            'symbol': txn['tokenSymbol'],
            'id': txn['tokenID'],
            'from': txn['from'],
            'to': txn['to']
        })

    return {'ERC-721': erc721_summary}


def _processErc1155Txns(txns_erc1155: list) -> dict:
    erc1155_summary = []
    for txn in txns_erc1155:
        # TokenName represents count of 1155 token
        erc1155_summary.append({
            'value': float(txn['TokenName']),
            'contract': txn['ContractAddress'],
            'name': txn['TokenSymbol'],
            'symbol': txn['TokenSymbol'],
            'id': txn['TokenId'],
            'from': txn['From'],
            'to': txn['To']
        })

    return {'ERC-1155': erc1155_summary}


def enrichTxn(txn_grouped: dict) -> dict:
    txn_grouped_enriched = txn_grouped
    txn_normal = txn_grouped['txn_normal']
    timestamp = int(txn_normal['timeStamp'])

    # Process gas and ETH
    gas_amount = float(Web3.fromWei(int(txn_normal['gasPrice']) * int(txn_normal['gasUsed']), 'ether'))
    eth_amount = float(Web3.fromWei(int(txn_normal['value']), 'ether'))

    # Add gas and ETH details of the given transaction
    # amount is in ether
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

    # Process ERC-1155 tokens in transaction
    erc1155_summary = _processErc1155Txns(txn_grouped['txn_erc1155'])
    assert not dict(txn_grouped_enriched.items() & erc1155_summary.items())  # make sure no overlap
    txn_grouped_enriched.update(erc1155_summary)

    return txn_grouped_enriched


def _timestampLessThan(txn_a, txn_b):
    return txn_a['timestamp'] < txn_b['timestamp']


def _describeNFTs(erc20s, erc721s, erc1155s):
    nft_str_list = []
    for erc20 in erc20s:
        nft_str_list.append("{:.5f} {}".format(erc20['value'], erc20['symbol']))

    for erc721 in erc721s:
        nft_str_list.append("{}-{}".format(erc721['symbol'], erc721['id']))

    for erc1155 in erc1155s:
        nft_str_list.append("{:.1f}x {}-{}".format(erc1155['value'], erc1155['symbol'], erc1155['id']))

    return ", ".join(nft_str_list)


def _describeEtherscanTxn(txn, my_wallets):
    eth_data = txn['ETH']
    gas_data = txn['gas']
    addr_from = eth_data['from'].lower()
    addr_to = eth_data['to'].lower()

    # internal transfer between wallets
    if addr_from in my_wallets and addr_to in my_wallets:
        txn_type = 'transfer'
        describe_str = 'Transfer {:.5f}E (worth ${:.2f}) from 0x...{} to 0x...{} ' \
                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'], eth_data['value_usd'],
                                                                 addr_from[-5:], addr_to[-5:],
                                                                 gas_data['amount'], gas_data['value_usd'])
    # transfer from Coinbase
    elif addr_from in COINBASE_WALLETS and addr_to in my_wallets:
        txn_type = 'transfer_from_coinbase'
        describe_str = 'Transfer {:.5f}E (worth ${:.2f}) from Coinbase to 0x...{} ' \
                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'], eth_data['value_usd'],
                                                                 addr_to[-5:],
                                                                 gas_data['amount'], gas_data['value_usd'])
    # transfer back to Coinbase
    elif addr_to in COINBASE_WALLETS:
        txn_type = 'transfer_to_coinbase'
        describe_str = 'Transfer {:.5f}E (worth ${:.2f}) from 0x...{} to Coinbase ' \
                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'], eth_data['value_usd'],
                                                                 addr_from[-5:],
                                                                 gas_data['amount'], gas_data['value_usd'])
    # Transfer via Ronin bridge
    elif addr_to in RONIN_BRIDGE:
        txn_type = 'transfer_to_ronin'
        describe_str = 'Transfer {:.5f}E (worth ${:.2f}) from 0x...{} to Ronin ' \
                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'], eth_data['value_usd'],
                                                                 addr_from[-5:],
                                                                 gas_data['amount'], gas_data['value_usd'])
    # Transfer via Ronin bridge
    elif addr_to in POLYGON_BRIDGE:
        txn_type = 'transfer_to_polygon'
        describe_str = 'Transfer {:.5f}E (worth ${:.2f}) from 0x...{} to Polygon ' \
                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'], eth_data['value_usd'],
                                                                 addr_from[-5:],
                                                                 gas_data['amount'], gas_data['value_usd'])

    # NFTs involved
    elif len(txn['ERC-20'] + txn['ERC-721'] + txn['ERC-1155']):
        nft_str = _describeNFTs(txn['ERC-20'], txn['ERC-721'], txn['ERC-1155'])

        # ETH from wallet, pay to buy NFT
        if addr_from in my_wallets:
            txn_type = 'buy_nft'
            describe_str = 'Buy {} for {:.5f}E (worth ${:.2f}) for 0x...{} ' \
                           'with {:.5f}E gas (worth ${:.2f})'.format(nft_str, eth_data['amount'], eth_data['value_usd'],
                                                                     addr_from[-5:],
                                                                     gas_data['amount'], gas_data['value_usd'])
        # ETH to wallet, receive from NFT sale
        elif addr_to in my_wallets:
            txn_type = 'sell_nft'
            describe_str = 'Sell {} for {:.5f}E (worth ${:.2f}) for 0x...{} ' \
                           'with {:.5f}E gas (worth ${:.2f})'.format(nft_str, eth_data['amount'], eth_data['value_usd'],
                                                                     addr_to[-5:],
                                                                     gas_data['amount'], gas_data['value_usd'])
        # my wallets not involved, not expected transaction
        else:
            txn_type = 'unknown'
            describe_str = 'Transfer {}, {:.5f}E (worth ${:.2f}) from 0x...{} to 0x...{} ' \
                           'with {:.5f}E gas (worth ${:.2f})'.format(nft_str,
                                                                     eth_data['amount'], eth_data['value_usd'],
                                                                     addr_from[-5:], addr_to[-5:],
                                                                     gas_data['amount'], gas_data['value_usd'])

            raise Exception('Unknown transaction type {}\n{}'.format(txn_type, describe_str))

    # ETH from my address, and no NFTs involved
    elif addr_from in my_wallets:
        contract = getContract(addr_to)

        if isContract(contract):
            func_name = findFunction(contract, txn['txn_normal']['input'])
            #print(func_name)
            if txn['txn_normal']['isError'] == '1':
                txn_type = 'failed_txn'
                describe_str = 'Function {} failed with {:.5f}E gas (worth ${:.2f})'.format(func_name,
                                                                                            gas_data['amount'],
                                                                                            gas_data['value_usd'])

            elif addr_to in WETH_CONTRACT and func_name != 'approve':
                match func_name:
                    case 'deposit':
                        txn_type = 'wrap_ETH'
                        describe_str = 'Wrap {:.5f}E (worth ${:.2f}) to WETH ' \
                                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'],
                                                                                 eth_data['value_usd'],
                                                                                 gas_data['amount'],
                                                                                 gas_data['value_usd'])
                    case 'withdraw':
                        txn_type = 'unwrap_ETH'
                        describe_str = 'Unwrap {:.5f}E (worth ${:.2f}) WETH ' \
                                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'],
                                                                                 eth_data['value_usd'],
                                                                                 gas_data['amount'],
                                                                                 gas_data['value_usd'])

                    case _:
                        raise Exception('Unknown interaction (function {}) with WETH contract'.format(func_name))

            else:
                match func_name:
                    # TODO: handle these better, associate them with contracts
                    case 'registerProxy' | 'cancelOrder_' | 'joinWhitelist' | 'bid':
                        txn_type = 'misc_expense'   # Approve wallet
                        describe_str = 'Function {} cost {:.5f}E (worth ${:.2f}) ' \
                                       'with {:.5f}E gas (worth ${:.2f})'.format(func_name,
                                                                                 eth_data['amount'],
                                                                                 eth_data['value_usd'],
                                                                                 gas_data['amount'],
                                                                                 gas_data['value_usd'])

                    case 'setApprovalForAll' | 'approve':
                        txn_type = 'approve_contract'   # Approve contract
                        describe_str = 'Approving {} contract ' \
                                       'with {:.5f}E gas (worth ${:.2f})'.format(contract['ContractName'],
                                                                                 gas_data['amount'],
                                                                                 gas_data['value_usd'])

                    case 'takingTickets':
                        txn_type = 'raffle'     # Buy raffle tickets
                        describe_str = 'Pay {:.5f}E to enter raffle ' \
                                       'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'],
                                                                                 gas_data['amount'],
                                                                                 gas_data['value_usd'])
                    case 'calculateMyResult':
                        txn_type = 'raffle_result'  # get raffle result back
                        eth_returned = 0
                        for t_i in txn['txn_internal']:
                            eth_returned += float(Web3.fromWei(int(t_i['value']), 'ether'))
                        describe_str = 'Check raffle result ({:.5f}E returned) ' \
                                       'with {:.5f}E gas (worth ${:.2f}'.format(eth_returned,
                                                                                gas_data['amount'],
                                                                                gas_data['value_usd'])

                    case _:
                        raise Exception('Unknown interaction (function {}) '
                                        'with {} contract {}'.format(func_name, contract['name'], addr_to[-5:]))

        else:
            txn_type = 'gift'
            describe_str = 'Gift {:.5f}E (worth ${:.2f}) to 0x...{} ' \
                           'with {:.5f}E gas (worth ${:.2f})'.format(eth_data['amount'], eth_data['value_usd'],
                                                                     addr_to[-5:],
                                                                     gas_data['amount'], gas_data['value_usd'])

    # ETH to my wallet, and no NFTs involved
    elif addr_to in my_wallets:
        txn_type = 'receive_gift'
        describe_str = 'Receive {:.5f}E (worth ${:.2f}) ' \
                       'from 0x...{}'.format(eth_data['amount'], eth_data['value_usd'],
                                             addr_from[-5:],
                                             gas_data['amount'], gas_data['value_usd'])

    else:
        raise Exception('Unknown transaction {}'.format(txn['txn_normal']['txn_hash']))

    print(describe_str)
    return {
        'type': txn_type,
        'ETH': eth_data,
        'gas': gas_data,
        'NFTs': {
            'ERC-20': txn['ERC-20'],
            'ERC-721': txn['ERC-721'],
            'ERC-1155': txn['ERC-1155'],
        },
        'description': describe_str,
        'timestamp': txn['timestamp'],
        'id': txn['txn_hash']
    }


def _describeCoinbaseTxn(txn, asset, my_wallets):
    if txn['Asset'].lower() == asset.lower():
        is_transfer = is_gift = False

        txn_type_raw = txn['Transaction Type'].lower()
        if txn_type_raw != 'send' and txn_type_raw != 'buy':
            raise Exception('Unknown transaction type from coinbase {}'.format(txn_type_raw))

        # Send represents either internal transfer, or a gift transaction
        if txn_type_raw == 'send':
            is_transfer = True
            # TODO: this should have been created in an enrichment step, not description
            addr_target = txn['Notes'].split()[-1].lower()

            if addr_target not in my_wallets:
                is_gift = True
                txn_type = 'gift'
            else:
                # i.e. a transfer initiated from Coinbase
                txn_type = 'transfer_by_coinbase'
        else:
            txn_type = txn_type_raw
            addr_target = ''

        # TODO: this should have been created in an enrichment step, not description
        eth_data = {
            'amount': float(txn['Quantity Transacted']),
            'value_usd': float(txn['Quantity Transacted']) * float(txn['Spot Price at Transaction']),
            'to': addr_target
        }
        gas_data = {
            # transfer fee is baked in
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

    # the oldest to the latest transactions by timestamp
    coinbase_txns.sort(key=sortByTimestamp)
    etherscan_txns.sort(key=sortByTimestamp)
    eth_descriptions = []

    i = j = 0
    max_i = len(coinbase_txns) - 1
    max_j = len(etherscan_txns) - 1
    # Iterate over two list of transactions, by ascending timestamp in both lists
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
        elif _timestampLessThan(coinbase_txns[i], etherscan_txns[j]):
            eth_descriptions.append(_describeCoinbaseTxn(coinbase_txns[i], "ETH", my_wallets))
            i += 1
        # else - etherscan txn timestamp earlier (smaller)
        else:
            eth_descriptions.append(_describeEtherscanTxn(etherscan_txns[j], my_wallets))
            j += 1

    # remove empty transactions, not relevant to ETH
    eth_descriptions = [x for x in eth_descriptions if x]
    return eth_descriptions
