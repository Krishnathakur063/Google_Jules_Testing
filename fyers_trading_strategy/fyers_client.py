import webbrowser
import os
from fyers_apiv3 import fyersModel
from fyers_trading_strategy import config

class FyersClient:
    """
    A client for interacting with the Fyers API.
    Handles authentication and data fetching.
    """
    ACCESS_TOKEN_FILE = ".fyers_access_token"

    def __init__(self):
        """
        Initializes the FyersClient.
        """
        self.client_id = config.CLIENT_ID
        self.secret_key = config.SECRET_KEY
        self.redirect_uri = config.REDIRECT_URI
        self.access_token = self._get_saved_access_token()

        self.fyers = fyersModel.FyersModel(
            client_id=self.client_id,
            token=self.access_token,
            log_path=os.path.join(os.getcwd(), "fyers_logs")
        )

        if not self.access_token:
            self._authenticate()

    def _get_saved_access_token(self):
        """
        Retrieves the access token from a local file if it exists.
        """
        if os.path.exists(self.ACCESS_TOKEN_FILE):
            with open(self.ACCESS_TOKEN_FILE, 'r') as f:
                return f.read().strip()
        return None

    def _save_access_token(self, access_token):
        """
        Saves the access token to a local file.
        """
        with open(self.ACCESS_TOKEN_FILE, 'w') as f:
            f.write(access_token)

    def _authenticate(self):
        """
        Handles the full authentication flow.
        """
        auth_code = self._generate_auth_code()
        self._set_access_token(auth_code)

        # Re-initialize the fyers model with the new token
        self.fyers = fyersModel.FyersModel(
            client_id=self.client_id,
            token=self.access_token,
            log_path=os.path.join(os.getcwd(), "fyers_logs")
        )

    def _generate_auth_code(self):
        """
        Generates the authentication URL and prompts the user for the auth code.
        """
        session = fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            response_type="code",
            grant_type="authorization_code"
        )

        auth_url = session.generate_authcode()
        print(f"Please log in to Fyers and authorize the app. Opening URL: {auth_url}")
        webbrowser.open(auth_url, new=2)

        auth_code = input("Please enter the auth code from the redirect URL: ")
        return auth_code

    def _set_access_token(self, auth_code):
        """
        Exchanges the auth code for an access token and saves it.
        """
        session = fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            response_type="code",
            grant_type="authorization_code"
        )
        session.set_token(auth_code)
        response = session.generate_token()

        if response.get("access_token"):
            self.access_token = response["access_token"]
            self._save_access_token(self.access_token)
            print("Access token generated and saved successfully.")
        else:
            raise Exception(f"Failed to generate access token: {response}")

    def get_historical_data(self, symbol, start_date, end_date):
        """
        Fetches historical data for a given symbol.

        :param symbol: The trading symbol (e.g., "NSE:NIFTY50-INDEX").
        :param start_date: The start date in 'YYYY-MM-DD' format.
        :param end_date: The end date in 'YYYY-MM-DD' format.
        :return: A list of historical data candles.
        """
        data = {
            "symbol": symbol,
            "resolution": config.TIMEFRAME,
            "date_format": "1",
            "range_from": start_date,
            "range_to": end_date,
            "cont_flag": "1"
        }
        response = self.fyers.history(data=data)
        if response.get("code") == 200 and response.get("candles"):
            return response["candles"]
        else:
            print(f"Error fetching historical data for {symbol}: {response}")
            return []

    def get_option_chain(self, symbol):
        """
        Fetches the option chain for a given symbol.
        Note: The Fyers API v3 option chain endpoint seems to provide data for
        the nearest weekly expiry by default. Handling specific expiries will require
        more detailed symbol management. For now, we fetch the available chain.

        :param symbol: The underlying symbol (e.g., "NSE:NIFTY50-INDEX").
        :return: The option chain data.
        """
        data = {
            "symbol": symbol,
            "strikecount": 20 # Fetch a decent number of strikes
        }
        response = self.fyers.option_chain(data=data)

        if response.get("code") == 200 and response.get("data"):
            return response["data"]
        else:
            print(f"Error fetching option chain for {symbol}: {response}")
            return None

if __name__ == '__main__':
    # This is for testing the authentication flow
    try:
        client = FyersClient()
        profile = client.fyers.get_profile()
        if profile.get('data'):
            print("Successfully connected to Fyers API.")
            print(f"Profile: {profile['data']}")
        else:
            print(f"Failed to get profile: {profile}")
    except Exception as e:
        print(f"An error occurred: {e}")
