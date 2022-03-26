
def _adjustCostBasisByEth(cost_basis, eth, method='HIFO'):
    def sortByPrice(x):
        return x['unit_price_usd']

    # 0 ETH transaction
    # TODO: handle 0 transfer but with fees (use to cancel transactions)
    if not eth:
        return cost_basis, {}

    # Increase in ETH = add cost
    elif eth > 0:
        cost_basis.append({'amount': eth, 'unit_price_usd': 0})
        return cost_basis, {}

    # Decrease in ETH = reduce cost, i.e. tax event
    else:   # eth < 0
        # Sort by price
        # TODO: support more cost basis types, FIFO, LIFO, average cost
        match method:
            case _:     # 'HIFO:'
                # sort transactions by descending cost
                cost_basis.sort(reverse=True, key=sortByPrice)

        tax_base = proceeds = 0
        eth_cost = -eth
        # Reduce cost from current item, until all cost is accounted and deducted
        for cost_i in cost_basis:
            # current item enough to account for cost
            if eth_cost <= cost_i['amount']:
                tax_base = cost_i['unit_price_usd'] * eth_cost
                cost_i['amount'] -= eth_cost
                eth_cost = 0
                break

            # current item fully exhausted by remaining cost
            else:
                tax_base = cost_i['unit_price_usd'] * cost_i['amount']
                eth_cost -= cost_i['amount']
                cost_i['amount'] = 0

        # All cost items exhausted, but still remaining cost
        if eth_cost != 0:
            raise Exception('Not enough ETH to spend')

        # remove cost items with 0 amount left
        cost_basis = list(filter(lambda c: c['amount'] > 0, cost_basis))
        tax_event = {'cost_basis': tax_base, 'proceeds': proceeds}

    return cost_basis, tax_event


def _matchCoinbaseTransferPair(txn_by_coinbase, txn_from_coinbase, prev_state):
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

    cost_basis, tax_event = _adjustCostBasisByEth(prev_state['cost_basis'], transfer_cost_eth, method='HIFO')
    remaining_balance = sum([x['amount'] for x in cost_basis])

    state = {
        'timestamp': min(txn_by_coinbase['timestamp'], txn_from_coinbase['timestamp']),
        'remaining_balance': remaining_balance,
        'unit_price_usd_avg': sum([x['unit_price_usd'] * x['amount'] for x in cost_basis]) / remaining_balance,
        'cost_basis': cost_basis,
    }

    return state, tax_event


def analyzeEth(eth_txns_summary):
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

        match txn['type']:
            # Purchase ETH (With USD)
            case 'buy':
                cost_basis = prev_state['cost_basis']
                # Add new purchased amount with cost basis (including gas/fees)
                cost_basis.append({
                    'amount': txn['ETH']['amount'],
                    'unit_price_usd': (txn['ETH']['value_usd'] + txn['gas']['value_usd']) / txn['ETH']['amount']})
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
                    state, tax_event = _matchCoinbaseTransferPair(txn, txn_pair, prev_state)

                    tax_events.append(tax_event)

            case 'transfer_from_coinbase':
                # put it to a queue and try to match with a later transaction from etherscan
                if not temp_coinbase_transfers:
                    temp_coinbase_transfers.append(txn)
                # if something already in the queue, try to match it with current transaction
                else:
                    txn_pair = temp_coinbase_transfers.pop(0)
                    state, tax_event = _matchCoinbaseTransferPair(txn_pair, txn, prev_state)

                    tax_events.append(tax_event)

            case _:
                pass

        if state:
            balances.append(state)
            prev_state = state

    print()
    return balances
