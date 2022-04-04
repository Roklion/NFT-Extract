import priceIO
from constants import *


def _reduceCostBasisByEth(cost_basis, eth, cost_method):
    if eth > 0:
        raise Exception('cannot have transfer that costs less than nothing')

    # eth < 0
    # Decrease in ETH = reduce cost
    else:
        # Sort by price
        # TODO: support more cost basis types, FIFO, LIFO, average cost
        match cost_method:
            case _:     # COST_METHOD_HIFO
                # sort transactions by descending cost
                cost_basis.sort(reverse=True, key=SORT_FUNC_BY_PRICE)

        cost_reduced = []
        eth_cost = -eth
        # Reduce cost from current item, until all cost is accounted and deducted
        for cost_i in cost_basis:
            # current item enough to account for cost
            if eth_cost <= cost_i['amount']:
                cost_reduced.append({
                    'amount': eth_cost,
                    'unit_price_usd': cost_i['unit_price_usd']
                })
                cost_i['amount'] -= eth_cost
                eth_cost = 0
                break

            # current item fully exhausted by remaining cost
            else:
                cost_reduced.append({
                    'amount': cost_i['amount'],
                    'unit_price_usd': cost_i['unit_price_usd']
                })
                eth_cost -= cost_i['amount']
                cost_i['amount'] = 0

        # All cost items exhausted, but still remaining cost
        if eth_cost != 0:
            raise Exception('Not enough ETH to spend')

        # remove cost items with 0 amount left
        cost_basis = list(filter(lambda c: c['amount'] > 0, cost_basis))

    return cost_basis, cost_reduced


def _increaseCostBasisToEth(cost_basis, cost, cost_method):
    if cost < 0:
        raise Exception('cannot increase cost basis by negative amount')

    # eth < 0
    else:
        # Sort by price
        # TODO: support more cost basis types, FIFO, LIFO, average cost
        match cost_method:
            # COST_METHOD_HIFO
            case _:
                # sort transactions by descending cost
                cost_basis.sort(reverse=True, key=SORT_FUNC_BY_PRICE)

        # remove cost items with 0 amount left
        cost_basis = list(filter(lambda c: c['amount'] > 0, cost_basis))
        # increase average cost of ETH
        cost_basis[0]['unit_price_usd'] += cost / cost_basis[0]['amount']

    return cost_basis


def _calculateTaxEvent(cost_basis, price_sold):
    tax_base = proceeds = 0
    for cost_i in cost_basis:
        tax_base += cost_i['unit_price_usd'] * cost_i['amount']
        proceeds += price_sold * cost_i['amount']

    return {'cost_basis': tax_base, 'proceeds': proceeds}


def _matchCoinbaseTransferPair(txn_by_coinbase, txn_from_coinbase, prev_state, cost_method):
    # two transactions should be 1 initiated by Coinbase, 1 received from Coinbase
    if txn_from_coinbase['type'] != 'transfer_from_coinbase':
        raise Exception('adjacent coinbase transfers are not matching pair')
    # two transactions shouldn't be too distant apart
    if abs(txn_by_coinbase['timestamp'] - txn_from_coinbase['timestamp']) > 100:
        raise Exception('two coinbase transfers too far apart')
    # two transactions should have the same target (receipt wallet)
    if txn_from_coinbase['ETH']['to'] != txn_by_coinbase['ETH']['to']:
        raise Exception('adjacent coinbase transfers are not for the same address')

    # implied transaction cost = difference in sent amount vs received amount
    transfer_cost_eth = txn_from_coinbase['ETH']['amount'] - txn_by_coinbase['ETH']['amount']
    cost_basis, cost_reduced = _reduceCostBasisByEth(prev_state['cost_basis'], transfer_cost_eth, cost_method)

    # order of operation:
    #   1. Sold ETH at spot price (Tax Event)
    #   2. Use proceeds from 1 to pay expense
    #   3. Value of 2 is added to ETH cost basis because it is necessary expense to continue investing with ETH
    timestamp = max(txn_by_coinbase['timestamp'], txn_from_coinbase['timestamp'])
    tax_event = _calculateTaxEvent(cost_reduced, priceIO.getEthPrice(timestamp))
    new_cost_basis = _increaseCostBasisToEth(cost_basis, tax_event['proceeds'], cost_method)

    remaining_balance = sum([x['amount'] for x in new_cost_basis])
    state = {
        'timestamp': min(txn_by_coinbase['timestamp'], txn_from_coinbase['timestamp']),
        'remaining_balance': remaining_balance,
        'unit_price_usd_avg': sum([x['unit_price_usd'] * x['amount'] for x in new_cost_basis]) / remaining_balance,
        'cost_basis': new_cost_basis,
    }

    return state, tax_event


def analyzeEth(eth_txns_summary, cost_method=COST_METHOD_HIFO):
    # Track 2 key metrics: balance and tax events
    #   Balance needs to be tracked as "state" that evolve over the timeline
    #   Tax Events needs previous state and current transaction
    balances = []
    tax_events = []
    prev_state = {
        'timestamp': 0,
        'balance': 0.0,
        'cost_basis': [],
    }
    temp_coinbase_transfers = []

    for txn in eth_txns_summary:
        state = {}
        cost_basis = prev_state['cost_basis']

        match txn['type']:
            # Purchase ETH (With USD)
            case 'buy':
                # Add new purchased amount with cost basis (including gas/fees)
                cost_basis.append({
                    'amount': txn['ETH']['amount'],
                    'unit_price_usd': priceIO.getEthPrice(txn['timestamp'])
                })
                # NOT tax event
                remaining_balance = sum([x['amount'] for x in cost_basis])
                state = {
                    'timestamp': txn['timestamp'],
                    'remaining_balance': remaining_balance,
                    'unit_price_usd_avg':
                        sum([x['unit_price_usd'] * x['amount'] for x in cost_basis]) / remaining_balance,
                    'cost_basis': cost_basis,
                }

            # Transfer to own wallet, transaction initiated by Coinbase
            case 'transfer_by_coinbase':
                # put it to a queue and try to match with a later transaction from etherscan
                if not temp_coinbase_transfers:
                    temp_coinbase_transfers.append(txn)
                # if something already in the queue, try to match it with current transaction
                else:
                    txn_pair = temp_coinbase_transfers.pop(0)
                    state, tax_event = _matchCoinbaseTransferPair(txn, txn_pair, prev_state, cost_method)
                    tax_events.append(tax_event)

            case 'transfer_from_coinbase':
                # put it to a queue and try to match with a later transaction from etherscan
                if not temp_coinbase_transfers:
                    temp_coinbase_transfers.append(txn)
                # if something already in the queue, try to match it with current transaction
                else:
                    txn_pair = temp_coinbase_transfers.pop(0)
                    state, tax_event = _matchCoinbaseTransferPair(txn_pair, txn, prev_state, cost_method)
                    tax_events.append(tax_event)

            # TODO handle ronin/polygon tokens
            case 'transfer' | 'transfer_to_ronin' | 'transfer_to_polygon':
                new_cost_basis, cost_reduced = _reduceCostBasisByEth(cost_basis, -txn['gas']['amount'],
                                                                     cost_method)
                # the reduced cost is used to pay expense, thus increasing USD cost of remaining ETH
                tax_event = _calculateTaxEvent(cost_reduced, priceIO.getEthPrice(txn['timestamp']))
                tax_events.append(tax_event)
                new_cost_basis = _increaseCostBasisToEth(new_cost_basis, tax_event['proceeds'], cost_method)

                # NOT tax event
                remaining_balance = sum([x['amount'] for x in new_cost_basis])
                state = {
                    'timestamp': txn['timestamp'],
                    'remaining_balance': remaining_balance,
                    'unit_price_usd_avg':
                        sum([x['unit_price_usd'] * x['amount'] for x in new_cost_basis]) / remaining_balance,
                    'cost_basis': new_cost_basis,
                }

            case 'gift':
                eth_reduction = txn['ETH']['amount']
                new_cost_basis, _ = _reduceCostBasisByEth(cost_basis, -eth_reduction, cost_method)
                # gift is NOT tax event, but cost is
                gas_cost = txn['gas']['amount'] if 'amount' in txn['gas'] else 0
                if gas_cost:
                    new_cost_basis, cost_reduced = _reduceCostBasisByEth(new_cost_basis, -gas_cost, cost_method)
                    tax_event = _calculateTaxEvent(cost_reduced, priceIO.getEthPrice(txn['timestamp']))
                    tax_events.append(tax_event)
                    new_cost_basis = _increaseCostBasisToEth(new_cost_basis, tax_event['proceeds'], cost_method)
                else:
                    new_cost_basis = cost_basis

                remaining_balance = sum([x['amount'] for x in new_cost_basis])
                state = {
                    'timestamp': txn['timestamp'],
                    'remaining_balance': remaining_balance,
                    'unit_price_usd_avg':
                        sum([x['unit_price_usd'] * x['amount'] for x in new_cost_basis]) / remaining_balance,
                    'cost_basis': new_cost_basis
                }

            # could be receiving gift or raffle returns, does not make a difference
            case 'receive_gift':
                cost_basis.append({
                    'amount': txn['ETH']['amount'],
                    'unit_price_usd': priceIO.getEthPrice(txn['timestamp'])
                })

                # cost is tax event
                gas_cost = txn['gas']['amount'] if 'amount' in txn['gas'] else 0
                if gas_cost:
                    cost_basis, cost_reduced = _reduceCostBasisByEth(cost_basis, -gas_cost, cost_method)
                    tax_event = _calculateTaxEvent(cost_reduced, priceIO.getEthPrice(txn['timestamp']))
                    tax_events.append(tax_event)
                    new_cost_basis = _increaseCostBasisToEth(cost_basis, tax_event['proceeds'], cost_method)
                else:
                    new_cost_basis = cost_basis

                remaining_balance = sum([x['amount'] for x in new_cost_basis])
                state = {
                    'timestamp': txn['timestamp'],
                    'remaining_balance': remaining_balance,
                    'unit_price_usd_avg':
                        sum([x['unit_price_usd'] * x['amount'] for x in new_cost_basis]) / remaining_balance,
                    'cost_basis': new_cost_basis
                }

            case 'misc_expense':
                eth_reduction = txn['ETH']['amount'] + (txn['gas']['amount'] if 'amount' in txn['gas'] else 0)
                new_cost_basis, cost_reduced = _reduceCostBasisByEth(cost_basis, -eth_reduction, cost_method)
                # the reduced cost is used to pay expense, thus increasing USD cost of remaining ETH
                tax_event = _calculateTaxEvent(cost_reduced, priceIO.getEthPrice(txn['timestamp']))
                tax_events.append(tax_event)
                new_cost_basis = _increaseCostBasisToEth(new_cost_basis, tax_event['proceeds'], cost_method)

                remaining_balance = sum([x['amount'] for x in new_cost_basis])
                state = {
                    'timestamp': txn['timestamp'],
                    'remaining_balance': remaining_balance,
                    'unit_price_usd_avg':
                        sum([x['unit_price_usd'] * x['amount'] for x in new_cost_basis]) / remaining_balance,
                    'cost_basis': new_cost_basis
                }

            case 'failed_txn':
                eth_reduction = txn['gas']['amount']
                new_cost_basis, cost_reduced = _reduceCostBasisByEth(cost_basis, -eth_reduction, cost_method)
                # the reduced cost is used to pay expense, thus increasing USD cost of remaining ETH
                tax_event = _calculateTaxEvent(cost_reduced, priceIO.getEthPrice(txn['timestamp']))
                tax_events.append(tax_event)
                new_cost_basis = _increaseCostBasisToEth(new_cost_basis, tax_event['proceeds'], cost_method)

                # TODO add cost to contract instead
                remaining_balance = sum([x['amount'] for x in new_cost_basis])
                state = {
                    'timestamp': txn['timestamp'],
                    'remaining_balance': remaining_balance,
                    'unit_price_usd_avg':
                        sum([x['unit_price_usd'] * x['amount'] for x in new_cost_basis]) / remaining_balance,
                    'cost_basis': new_cost_basis
                }

            case 'transfer_nft' | 'send_nft':
                eth_reduction = txn['gas']['amount'] if 'amount' in txn['gas'] else 0
                new_cost_basis, cost_reduced = _reduceCostBasisByEth(cost_basis, -eth_reduction, cost_method)

                tax_event = _calculateTaxEvent(cost_reduced, priceIO.getEthPrice(txn['timestamp']))
                tax_events.append(tax_event)

                # TODO transfer cost to NFTs
                remaining_balance = sum([x['amount'] for x in new_cost_basis])
                state = {
                    'timestamp': txn['timestamp'],
                    'remaining_balance': remaining_balance,
                    'unit_price_usd_avg':
                        sum([x['unit_price_usd'] * x['amount'] for x in new_cost_basis]) / remaining_balance,
                    'cost_basis': new_cost_basis
                }

            case 'buy_nft' | 'approve_contract' | 'exchange' | 'wrap_ETH':
                eth_reduction = (txn['ETH']['amount'] if 'amount' in txn['ETH'] else 0) + \
                                (txn['gas']['amount'] if 'amount' in txn['gas'] else 0)
                new_cost_basis, cost_reduced = _reduceCostBasisByEth(cost_basis, -eth_reduction, cost_method)

                tax_event = _calculateTaxEvent(cost_reduced, priceIO.getEthPrice(txn['timestamp']))
                tax_events.append(tax_event)

                # TODO handle outbound NFT costs (exchange)
                # TODO transfer cost to NFTs
                remaining_balance = sum([x['amount'] for x in new_cost_basis])
                state = {
                    'timestamp': txn['timestamp'],
                    'remaining_balance': remaining_balance,
                    'unit_price_usd_avg':
                        sum([x['unit_price_usd'] * x['amount'] for x in new_cost_basis]) / remaining_balance,
                    'cost_basis': new_cost_basis
                }

            case 'sell_nft' | 'unwrap_ETH':
                # Add new purchased amount with cost basis (including gas/fees)
                cost_basis.append({
                    'amount': txn['ETH']['amount'],
                    'unit_price_usd': priceIO.getEthPrice(txn['timestamp'])
                })

                # TODO handle NFT sale tax event
                remaining_balance = sum([x['amount'] for x in cost_basis])
                state = {
                    'timestamp': txn['timestamp'],
                    'remaining_balance': remaining_balance,
                    'unit_price_usd_avg':
                        sum([x['unit_price_usd'] * x['amount'] for x in cost_basis]) / remaining_balance,
                    'cost_basis': cost_basis,
                }

            case 'burn_nft':
                # TODO implement this
                pass

            case 'receive_nft_gift':
                # TODO implement this
                pass

            case 'ignore':
                pass

            case _:
                raise Exception('Unknown transaction type {} cannot be processed'.format(txn['type']))

        if state:
            print(txn['description'])
            print(state['remaining_balance'])
            balances.append(state)
            prev_state = state

    return balances
