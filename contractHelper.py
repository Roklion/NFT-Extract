import json
import web3


def isContract(contract):
    return len(contract['SourceCode']) > 0


def findFunction(contract, txn_input):
    abi = json.loads(contract['ABI'])
    for i in abi:
        if i['type'] != 'function':
            continue
        else:
            func_str = i['name'] + '({})'.format(','.join([x['type'] for x in i['inputs']]))
            func_hex = web3.Web3.keccak(text=func_str)[:4].hex()
            if func_hex == txn_input[:10]:
                return i['name']

    return ''

