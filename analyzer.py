

def _adjustCostBasisByEth(cost_basis, eth, method='HIFO'):
    def sortByPrice(x):
        return x['unit_price_usd']

    if not eth:
        return cost_basis, {}

    elif eth > 0:
        cost_basis.append({'amount': eth, 'unit_price_usd': 0})
        return cost_basis, {}

    else:   # eth <0
        # Sort by price
        match method:
            case _:     # 'HIFO:'
                cost_basis.sort(reverse=True, key=sortByPrice)

        tax_base = proceeds = 0
        eth_cost = -eth
        for cost_i in cost_basis:
            if eth_cost <= cost_i['amount']:
                tax_base = cost_i['unit_price_usd'] * eth_cost
                cost_i['amount'] -= eth_cost
                eth_cost = 0
                break

            else:
                tax_base = cost_i['unit_price_usd'] * cost_i['amount']
                eth_cost -= cost_i['amount']
                cost_i['amount'] = 0

        if eth_cost != 0:
            raise Exception('Not enough ETH to spend')

        cost_basis = list(filter(lambda c: c['amount'] > 0, cost_basis))
        tax_event = {'cost_basis': tax_base, 'proceeds': proceeds}

    return cost_basis, tax_event


def _matchCoinbaseTransferPair(txn_by_coinbase, txn_from_coinbase, prev_state):
    if txn_from_coinbase['type'] != 'transfer_from_coinbase':
        raise Exception('adjacent coinbase transfers are not matching pair')
    if abs(txn_by_coinbase['timestamp'] - txn_from_coinbase['timestamp']) > 100:
        raise Exception('two coinbase transfers too far apart')
    if txn_from_coinbase['ETH']['to'] != txn_by_coinbase['ETH']['to']:
        raise Exception('adjacent coinbase transfers are not for the same address')

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
            case 'buy':
                cost_basis = prev_state['cost_basis']
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

            case 'transfer_by_coinbase':
                # put it to a queue and try to match with a later transaction from etherscan
                if not temp_coinbase_transfers:
                    temp_coinbase_transfers.append(txn)
                else:
                    txn_pair = temp_coinbase_transfers.pop(0)
                    state, tax_event = _matchCoinbaseTransferPair(txn, txn_pair, prev_state)

                    tax_events.append(tax_event)

                print()

            case 'transfer_from_coinbase':
                # put it to a queue and try to match with a later transaction from etherscan
                if not temp_coinbase_transfers:
                    temp_coinbase_transfers.append(txn)
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
