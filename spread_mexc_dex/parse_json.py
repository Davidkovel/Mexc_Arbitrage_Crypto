import json


class JsonParse:
    def __init__(self):
        self.json_data: dict = {}

    def parse(self) -> dict:
        with open("spread_mexc_dex/tokens.json", "r") as f:
            data_from_json = json.load(f)
            for key, value in data_from_json.items():
                self.json_data[key] = {
                   'contract_address': value['contract_address'],
                   'chain': value['chain']
                }
        return self.json_data

if __name__ == "__main__":
    j = JsonParse()
    j.parse()
