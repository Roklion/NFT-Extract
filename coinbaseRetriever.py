import fileIO
from datetime import *


def getCoinbaseTxns(data_path):
    txns_raw = fileIO.getCoinbaseTxnsFromSpreadsheet(data_path)
    for txn in txns_raw:
        txn['time'] = datetime.strptime(txn['Timestamp'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        txn['timestamp'] = int(txn['time'].timestamp())
        del txn['Timestamp']

    return txns_raw
