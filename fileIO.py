import csv
import os


def getErc1155TxnsFromSpreadsheet(wallet, data_path):
    # assumption: a single data file (csv) will be placed under %data_path%/ERC1155
    path = data_path + "ERC1155/"
    for file in os.listdir(path):
        if file.endswith(".csv") and wallet.lower() in file.lower():
            with open(path + file, "r") as f:
                return list(csv.DictReader(f))
                # return([{k: v for k, v in row.items()}
                #     for row in csv.DictReader(f)])

    print("Cannot find ERC-1155 data file for ", wallet)
    return []


def getCoinbaseTxnsFromSpreadsheet(data_path):
    # assumption: a single data file (csv) will be placed under %data_path%/Coinbase,
    #   Spreadsheet is downloaded from transaction report
    path = data_path + "Coinbase/"
    for file_name in os.listdir(path):
        if file_name.endswith(".csv"):
            with open(path + file_name, "r") as file:
                header_line = 0
                for line in file:
                    if line.startswith("Timestamp,"):
                        break
                    else:
                        header_line += 1

            with open(path + file_name, "r") as file:
                for i in range(header_line):
                    next(file)

                return list(csv.DictReader(file))

    print("Cannot find any Coinbase data file")
    return []
