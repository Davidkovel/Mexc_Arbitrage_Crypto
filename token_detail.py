# /api/v3/capital/config/getall - DETAIL OF TOKEN
import json
from http.client import responses

# api/v1/contract/detail  - LIST OF TOKENS

# ----


import requests
from typing import List, Dict, Optional
from mexc_api.spot import Spot

# Constants
CONTRACT_BASE_URL = "https://contract.mexc.com"
CAPITAL_BASE_URL = "https://api.mexc.com"
CONTRACT_ENDPOINT = "/api/v1/contract/detail"
CAPITAL_ENDPOINT = "/api/v3/capital/config/getall"
API_KEY = "mx0vgl0bqEgMXcjoPG"  # Replace with your actual API key
API_SECRET = "2850d847cf9947c09d432fc8f444f523"  # Replace with your actual API secret


class TokenService:
    def __init__(self, contract_base_url: str, capital_base_url: str, api_key: str, api_secret: str):
        self.contract_base_url = contract_base_url
        self.capital_base_url = capital_base_url
        self.api_key = api_key
        self.api_secret = api_secret

    def get_token_list(self) -> Optional[List[Dict]]:
        """Fetch the list of tokens from the contract endpoint."""
        url = f"{self.contract_base_url}{CONTRACT_ENDPOINT}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("code") == 0:
                return data.get("data", [])
            else:
                print("Failed to fetch token list:", data.get("message"))
        else:
            print("Failed to connect to the contract API:", response.status_code)
        return None

    def get_token_details(self, symbol: str) -> Optional[Dict]:
        """Fetch details of a specific token from the capital endpoint."""
        url = f"{self.capital_base_url}{CAPITAL_ENDPOINT}"
        headers = {"X-MEXC-APIKEY": self.api_key}
        params = {"symbol": symbol}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("code") == 0:
                return data.get("data", {})
            else:
                print(f"Failed to fetch details for token {symbol}:", data.get("message"))
        else:
            print(f"Failed to connect to the capital API for token {symbol}:", response.status_code)
        return None

    def extract_token_info(self, token_detail: Dict) -> Dict:
        """Extract required fields from the token details."""
        return {
            "depositEnable": token_detail.get("depositEnable"),
            "withdrawEnable": token_detail.get("withdrawEnable"),
            "contract": token_detail.get("contract"),
            "netWork": token_detail.get("netWork")
        }

    def process_tokens(self):
        """Process the list of tokens and print their details."""
        tokens = self.get_token_list()
        if tokens:
            for token in tokens:
                symbol = token.get("symbol")
                print(f"Processing token: {symbol}")

                token_detail = self.get_token_details(symbol)
                if token_detail:
                    token_info = self.extract_token_info(token_detail)
                    print(f"Token: {symbol}")
                    print(f"Deposit Enable: {token_info['depositEnable']}")
                    print(f"Withdraw Enable: {token_info['withdrawEnable']}")
                    print(f"Contract: {token_info['contract']}")
                    print(f"Network: {token_info['netWork']}")
                    print("-" * 40)


class SpotService:
    def __init__(self):
        self.spot = Spot(API_KEY, API_SECRET)
        self.wallet = self.spot.wallet
        self.market = self.spot.market

    def process_retrieve_data(self):
        data = self.wallet.info()
        results = []

        for i in data:
            if i is not None:
                coin = i['coin']
                is_available = self.check_futures_availability(coin)

                if not is_available:
                    print(f"{coin} is not available in futures. Skipping.")
                    self.save_to_json_file({"coin": coin, "error": "Not available in futures"})
                    continue

                network_info = i.get('networkList', [{}])[0]
                token_info = {
                    "coin": coin,
                    "depositEnable": network_info.get('depositEnable', False),
                    "withdrawEnable": network_info.get('withdrawEnable', False),
                    "contract": network_info.get('contract', "N/A"),
                    "chain": network_info.get('network', "N/A")
                }

                self.save_to_json_file(token_info)
                results.append(token_info)

        return results

    def check_dex_availability(self, coin: str, address_contract: str, chain: str) -> bool:
        base_url = "https://api.dexscreener.com/token-pairs/v1/"
        try:
            url = f"{base_url}/{chain}/{address_contract}"

            req = requests.get(base_url, timeout=5)
            req_json = req.json()
            if not req_json.get("success", False):
                return False

            return True
        except Exception as ex:
            print(f"[ERRROR] DEX {ex}")
            return False


    def check_futures_availability(self, symbol: str) -> bool:
        """Checks if a coin is available in futures."""
        symbol = symbol + "_USDT"
        endpoint = f"https://contract.mexc.com/api/v1/contract/fair_price/{symbol}"
        try:
            req = requests.get(endpoint, timeout=5)
            req_json = req.json()
            if not req_json.get("success", False):
                return False

            return True
        except requests.RequestException as e:
            print(f"Error checking futures availability for {symbol}: {e}")
            return False

    def save_to_json_file(self, data: dict):
        """Saves data to JSON file."""
        file_path = 'spread_mexc_dex/tokens.json'

        try:
            with open(file_path, 'r+') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = {}

                token_entry = {}
                if "contract" in data:
                    token_entry["contract_address"] = data["contract"]
                if "chain" in data:
                    token_entry["chain"] = data["chain"]

                if token_entry:
                    existing_data[data["coin"]] = token_entry

                f.seek(0)
                json.dump(existing_data, f, indent=4)
        except FileNotFoundError:
            with open(file_path, 'w') as f:
                json.dump({data["coin"]: token_entry}, f, indent=4)




class DexTokenChecker:
    def __init__(self, token_file: str):
        self.token_file = token_file

    def load_tokens(self) -> dict:
        """Загружает список токенов из файла JSON."""
        try:
            with open(self.token_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as ex:
            print(f"[ERROR] Failed to load tokens: {ex}")
            return {}

    def save_tokens(self, tokens: dict) -> None:
        """Сохраняет обновленный список токенов в файл JSON."""
        with open(self.token_file, 'w', encoding='utf-8') as file:
            json.dump(tokens, file, indent=4)

    def check_dex_availability(self, chain: str, contract_address: str) -> bool:
        """Проверяет доступность токена на DEX через DexScreener API."""
        base_url = f"https://api.dexscreener.com/token-pairs/v1/{chain}/{contract_address}"
        try:
            response = requests.get(base_url, timeout=5)
            response_json = response.json()
            if response_json == []:
                print(f"[DEBUG] DEX check failed: {response_json} - coin {chain} - {contract_address}")
                return False
        except Exception as ex:
            print(f"[ERROR] DEX check failed: {ex}")
            return False

    def clean_invalid_tokens(self) -> None:
        """Удаляет токены, которые недоступны на DEX, из tokens.json."""
        tokens = self.load_tokens()
        updated_tokens = {
            symbol: data for symbol, data in tokens.items()
            if self.check_dex_availability(data["chain"], data["contract_address"])
        }

        print(updated_tokens)
        if len(updated_tokens) != len(tokens):
            self.save_tokens(updated_tokens)
            print("Обновленный список токенов сохранен, недоступные токены удалены.")
        else:
            print("Все токены доступны, изменений нет.")





def test_api():
    try:

        url = f"https://futures.mexc.com/ru-RU/exchange/LL_USDT?type=linear_swap"
        r = requests.get(url)
        print(r.url)
    except Exception as ex:
        print(f"[ERROR] {ex}")


if __name__ == "__main__":
    # token_service = TokenService(CONTRACT_BASE_URL, CAPITAL_BASE_URL, API_KEY)
    # token_service.process_tokens()

    # spot = Spot(API_KEY, API_SECRET)
    # wallet = spot.wallet
    # market = spot.market
    # data = wallet.info()
    #
    # for i in data:
    #     coin = data['coin']
    #     depositEnable = data['depositEnable']
    #     withdrawEnable = data['withdrawEnable']
    #     contract = data['contract']
    #     chain = data['network']
    #
    # # https://contract.mexc.com/api/v1/contract/fair_price/BTC_USDT

    # service = SpotService()
    # service.process_retrieve_data()

    # checker = DexTokenChecker("spread_mexc_dex/tokens.json")
    # checker.clean_invalid_tokens()
    test_api()