import os
import requests
from dotenv import load_dotenv

load_dotenv()

class PiNetwork:
    def __init__(self):
        self.api_key = os.getenv("PI_API_KEY")
        self.wallet_private_seed = os.getenv("PI_WALLET_PRIVATE_SEED")
        self.base_url = "https://api.minepi.com/v2"
        self.headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_payment(self, payment_id):
        try:
            response = requests.get(
                f"{self.base_url}/payments/{payment_id}",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Pi API Error: {e}")
            return None

    def create_payment(self, payment_data):
        try:
            response = requests.post(
                f"{self.base_url}/payments",
                json=payment_data,
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 201:
                return response.json()
            return None
        except Exception as e:
            print(f"Pi Payment Creation Error: {e}")
            return None
