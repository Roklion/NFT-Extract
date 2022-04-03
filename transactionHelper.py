from etherscanIO import *
from contractHelper import *
from constants import *
import priceIO
from web3 import Web3


def groupByNormalTxns(txn_hash: str,
                      timeStamp: str,
                      txns_normal: dict,
                      txns_internal: list,
                      txns_erc20: list,
                      txns_erc721: list,
                      txns_erc1155: list) -> dict:
    # Different type of transactions can be joined by the same transaction hash
    return ({
        'txn_hash': txn_hash,
        'timeStamp': timeStamp,
        'txn_normal': [t for t in txns_normal if t['hash'] == txn_hash],
        'txn_internal': [t for t in txns_internal if t['hash'] == txn_hash],
        'txn_erc20': [t for t in txns_erc20 if t['hash'] == txn_hash],
        'txn_erc721': [t for t in txns_erc721 if t['hash'] == txn_hash],
        'txn_erc1155': [t for t in txns_erc1155 if t['hash'] == txn_hash]
    })


def _procesEthAndGasTxns(txns: list, timestamp: int) -> dict:
    # Process gas and ETH
    if len(txns) > 1:
        raise Exception("Two normal transactions for the same hash")
    elif not txns:
        return {}
    else:  # len = 1
        txn = txns[0]
        if 'gasPrice' not in txn:
            gas_amount = 0
        else:
            gas_amount = float(Web3.fromWei(int(txn['gasPrice']) * int(txn['gasUsed']), 'ether'))
        eth_amount = float(Web3.fromWei(int(txn['value']), 'ether'))

        # Add gas and ETH details of the given transaction
        # amount is in ether
        return {
            'gas': {
                'amount': gas_amount,
                'value_usd': gas_amount * priceIO.getTokenHistData("ethereum", "USD", timestamp)
            },
            'ETH': {
                'amount': eth_amount,
                'value_usd': eth_amount * priceIO.getTokenHistData("ethereum", "USD", timestamp),
                'from': txn['from'],
                'to': txn['to']
            },
        }


def _processErc20Txns(txns_erc20: list) -> dict:
    erc20_summary = []
    for txn in txns_erc20:
        # tokenDecimal is token precision
        # value represents integer to the most precise digit of the token
        decimal = 0 if not txn['tokenDecimal'] else int(txn['tokenDecimal'])
        erc20_summary.append({
            'value': float(txn['value']) / pow(10, decimal),
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
            'value': float(txn['tokenName']),
            'contract': txn['contractAddress'],
            'name': txn['tokenSymbol'],
            'symbol': txn['tokenSymbol'],
            'id': txn['tokenId'],
            'from': txn['from'],
            'to': txn['to']
        })

    return {'ERC-1155': erc1155_summary}


def enrichTxn(txn_grouped: dict) -> dict:
    txn_grouped_enriched = txn_grouped
    txn_grouped['timestamp'] = int(txn_grouped['timeStamp'])

    # Process gas and ETH from normal txn
    normal_txn_summary = _procesEthAndGasTxns(txn_grouped['txn_normal'], txn_grouped['timestamp'])
    txn_grouped_enriched.update({'Normal': normal_txn_summary})

    # Process internal transactions
    internal_txn_summary = _procesEthAndGasTxns(txn_grouped['txn_internal'], txn_grouped['timestamp'])
    txn_grouped_enriched.update({'Internal': internal_txn_summary})

    # Process ERC-20 tokens in transaction
    erc20_summary = _processErc20Txns(txn_grouped['txn_erc20'])
    txn_grouped_enriched.update(erc20_summary)

    # Process ERC-721 tokens in transaction
    erc721_summary = _processErc721Txns(txn_grouped['txn_erc721'])
    txn_grouped_enriched.update(erc721_summary)

    # Process ERC-1155 tokens in transaction
    erc1155_summary = _processErc1155Txns(txn_grouped['txn_erc1155'])
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


def _netEthAndGas(txn_normal, txn_internal, my_wallets):
    txn_from = [t for t in [txn_normal, txn_internal] if t and t['ETH']['from'] in my_wallets]
    txn_to = [t for t in [txn_normal, txn_internal] if t and t['ETH']['to'] in my_wallets]

    if not txn_from and not txn_to:
        raise Exception('transaction not interacting with wallets')

    net = {'amount': 0, 'value_usd': 0}
    for txn in txn_from:
        net['amount'] -= txn['ETH']['amount']
        net['value_usd'] -= txn['ETH']['value_usd']

    for txn in txn_to:
        net['amount'] += txn['ETH']['amount']
        net['value_usd'] += txn['ETH']['value_usd']

    ret_data = {
        'ETH': {
            'amount': abs(net['amount']),
            'value_usd': abs(net['value_usd'])
        },
        'gas': {
            'amount': sum([t['gas']['amount'] for t in txn_from]),
            'value_usd': sum([t['gas']['value_usd'] for t in txn_from]),
        }
    }
    # net outbound
    if net['amount'] < 0 or (txn_from and not txn_to):
        ret_data['ETH']['from'] = txn_from[0]['ETH']['from']
        ret_data['ETH']['to'] = txn_from[0]['ETH']['to']
    # net inbound
    else:
        ret_data['ETH']['from'] = txn_to[0]['ETH']['from']
        ret_data['ETH']['to'] = txn_to[0]['ETH']['to']

        # net inbound, and its not internal transfer, subtract gas fee from received ETH
        #   because from address has changed, gas won't be processed later
        if txn_from and txn_from[0]['ETH']['from'] in my_wallets and txn_to[0]['ETH']['to'] not in my_wallets:
            ret_data['ETH']['amount'] -= ret_data['gas']['amount']
            ret_data['ETH']['value_usd'] -= ret_data['gas']['value_usd']

    return ret_data


def _describeEtherscanTxn(txn, my_wallets):
    has_eth = txn['Normal'] or txn['Internal']
    has_nfts = len(txn['ERC-20'] + txn['ERC-721'] + txn['ERC-1155']) > 0

    # Only normal transactions
    if has_eth and not has_nfts:
        eth_and_gas = _netEthAndGas(txn['Normal'], txn['Internal'], my_wallets)
        eth_data = eth_and_gas['ETH']
        gas_data = eth_and_gas['gas']
        addr_from = eth_data['from'].lower()
        addr_to = eth_data['to'].lower()

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

        # ETH from my address, and no NFTs involved
        elif addr_from in my_wallets:
            contract = getContract(addr_to)

            if isContract(contract):
                func_name = findFunction(contract, txn['txn_normal'][0]['input'])

                if txn['txn_normal'][0]['isError'] == '1':
                    txn_type = 'failed_txn'
                    describe_str = 'Function {} failed ' \
                                   'with {:.5f}E gas (worth ${:.2f})'.format(func_name,
                                                                             gas_data['amount'], gas_data['value_usd'])

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
                            txn_type = 'misc_expense'  # Approve wallet
                            describe_str = 'Function {} cost {:.5f}E (worth ${:.2f}) ' \
                                           'with {:.5f}E gas (worth ${:.2f})'.format(func_name,
                                                                                     eth_data['amount'],
                                                                                     eth_data['value_usd'],
                                                                                     gas_data['amount'],
                                                                                     gas_data['value_usd'])

                        case 'setApprovalForAll' | 'approve':
                            txn_type = 'approve_contract'  # Approve contract
                            describe_str = 'Approving {} contract ' \
                                           'with {:.5f}E gas (worth ${:.2f})'.format(contract['ContractName'],
                                                                                     gas_data['amount'],
                                                                                     gas_data['value_usd'])

                        case 'takingTickets':
                            txn_type = 'raffle'  # Buy raffle tickets
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
            raise Exception('Unknown ETH transaction with no owned wallets involved {}'.format(txn['txn_hash']))

    # NFTs involved
    elif has_nfts:
        nft_str = _describeNFTs(txn['ERC-20'], txn['ERC-721'], txn['ERC-1155'])
        nft_froms = list(set(t['from'] for t in txn['ERC-20'] + txn['ERC-721'] + txn['ERC-1155']))
        nft_tos = list(set(t['to'] for t in txn['ERC-20'] + txn['ERC-721'] + txn['ERC-1155']))

        # No ETH involved
        if not txn['Normal'] and not txn['Internal']:
            # Only receiving NFTs
            if all([addr in my_wallets for addr in nft_tos]):
                # From known scam addresses
                if any([addr in IGNORE_ADDRESS for addr in nft_froms]):
                    txn_type = 'ignore'
                    describe_str = 'Receive {} as scam. Ignore transaction.'.format(nft_str)
                else:
                    txn_type = 'receive_nft_gift'
                    describe_str = 'Receive {} for free'.format(nft_str)
            # Only sending NFTs
            elif all([addr in my_wallets for addr in nft_froms]):
                # Send to burn
                if all([addr in BURN_ADDRESSES for addr in nft_tos]):
                    txn_type = 'burn_nft'
                    describe_str = 'Burn {} for free'.format(nft_str)
                else:
                    txn_type = 'gift_nft'
                    describe_str = 'Gift {} for free'.format(nft_str)
            # exchange NFT for NFT
            else:
                nft_to_str = _describeNFTs([t for t in txn['ERC-20'] if t['to'] in my_wallets],
                                           [t for t in txn['ERC-721'] if t['to'] in my_wallets],
                                           [t for t in txn['ERC-1155'] if t['to'] in my_wallets])
                nft_from_str = _describeNFTs([t for t in txn['ERC-20'] if t['from'] in my_wallets],
                                             [t for t in txn['ERC-721'] if t['from'] in my_wallets],
                                             [t for t in txn['ERC-1155'] if t['from'] in my_wallets])

                # TODO: ERC-20 can have gas
                txn_type = 'exchange'
                describe_str = 'Exchange {} for {}'.format(nft_to_str, nft_from_str)

            eth_data = {}
            gas_data = {}

        # ETH involved
        else:
            eth_and_gas = _netEthAndGas(txn['Normal'], txn['Internal'], my_wallets)
            eth_data = eth_and_gas['ETH']
            gas_data = eth_and_gas['gas']
            addr_from = eth_data['from'].lower()
            addr_to = eth_data['to'].lower()

            # ETH from wallet, pay to buy NFT
            if addr_from in my_wallets:
                # pay, but not receiving all NFTs
                if any([addr not in my_wallets for addr in nft_tos]):
                    contract = getContract(addr_to)
                    # exchange via contract functions
                    if isContract(contract):
                        func_name = findFunction(contract, txn['txn_normal'][0]['input'])

                        nft_to_str = _describeNFTs([t for t in txn['ERC-20'] if t['to'] in my_wallets],
                                                   [t for t in txn['ERC-721'] if t['to'] in my_wallets],
                                                   [t for t in txn['ERC-1155'] if t['to'] in my_wallets])
                        nft_from_str = _describeNFTs([t for t in txn['ERC-20'] if t['from'] in my_wallets],
                                                     [t for t in txn['ERC-721'] if t['from'] in my_wallets],
                                                     [t for t in txn['ERC-1155'] if t['from'] in my_wallets])

                        # No NFT received
                        if func_name == 'mintMany':
                            print("mintMany".format(txn['txn_hash']))

                        if not nft_to_str:
                            txn_type = 'send_nft'
                            describe_str = '{} {} with {:.5f}E (worth ${:.2f}） ' \
                                           'with {:.5f}E gas (worth ${:.2f})'.format(func_name, nft_from_str,
                                                                                     eth_data['amount'],
                                                                                     eth_data['value_usd'],
                                                                                     gas_data['amount'],
                                                                                     gas_data['value_usd'])
                        # no NFT sent, not possible in this branch
                        elif not nft_from_str:
                            raise Exception('Unknown ETH and NFT exchange')
                        # some NFT sent and some NFT received
                        else:
                            txn_type = 'exchange'
                            describe_str = '{} {} for {} + {:.5f}E (worth ${:.2f}） ' \
                                           'with {:.5f}E gas (worth ${:.2f})'.format(func_name,
                                                                                     nft_to_str, nft_from_str,
                                                                                     eth_data['amount'],
                                                                                     eth_data['value_usd'],
                                                                                     gas_data['amount'],
                                                                                     gas_data['value_usd'])

                    # Pay to burn
                    elif all([addr in BURN_ADDRESSES for addr in nft_tos]):
                        txn_type = 'burn_nft'
                        describe_str = 'Burn {} for {:.5f}E (worth ${:.2f}） ' \
                                       'with {:.5f}E gas (worth ${:.2f}'.format(nft_str,
                                                                                eth_data['amount'],
                                                                                eth_data['value_usd'],
                                                                                gas_data['amount'],
                                                                                gas_data['value_usd'])
                    else:
                        raise Exception('unknown method of exchanging NFTs')
                # Pay, received all NFTs
                else:
                    txn_type = 'buy_nft'
                    describe_str = 'Buy {} for {:.5f}E (worth ${:.2f}) ' \
                                   'with {:.5f}E gas (worth ${:.2f})'.format(nft_str,
                                                                             eth_data['amount'], eth_data['value_usd'],
                                                                             gas_data['amount'], gas_data['value_usd'])
            # ETH to wallet, receive from NFT sale
            elif addr_to in my_wallets:
                # Some NFTs not originated from my wallets
                if any([addr not in my_wallets for addr in nft_froms]):
                    raise Exception('unknown mean of exchange ETH and NFTs')

                txn_type = 'sell_nft'
                describe_str = 'Sell {} for {:.5f}E (worth ${:.2f}) ' \
                               'with {:.5f}E gas (worth ${:.2f})'.format(nft_str,
                                                                         eth_data['amount'], eth_data['value_usd'],
                                                                         gas_data['amount'], gas_data['value_usd'])
            # my wallets not involved, not expected transaction
            else:
                raise Exception('Unknown NFT ({}) transaction '
                                'with no owned wallets involved {}'.format(nft_str, txn['txn_hash']))

    else:
        raise Exception('Unknown transaction')

    # print(describe_str)
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
        'txn_hash': txn['txn_hash']
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
