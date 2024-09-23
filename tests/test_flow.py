# tests/test_flow.py

import os
import pandas as pd
import unittest
from config import API_KEY, API_URL
from stock_data_flow import StockDataProcessor

def create_dummy_csv(file_path: str) -> None:
    """Creates a dummy CSV file with a single row containing the symbol 'IBM'."""
    data = {'symbol': ['IBM']}
    df = pd.DataFrame(data)
    df.to_csv(file_path, sep=";", index=False)

class TestStockDataProcessor(unittest.TestCase):
    def setUp(self):
        # Create a dummy CSV file
        self.dummy_csv_path = 'dummy.csv'
        create_dummy_csv(self.dummy_csv_path)
        # Initialize the StockDataProcessor
        self.processor = StockDataProcessor(api_key=API_KEY, api_url=API_URL)

    def tearDown(self):
        # Clean up the dummy CSV file
        os.remove(self.dummy_csv_path)

    def test_api_call(self):
        """Tests the API call with the given parameters (API key 'demo' and symbol 'IBM')."""
        # Read the dummy CSV file
        df = self.processor.read_csv(file_path=self.dummy_csv_path)
        # Get the symbol from the CSV file
        symbol = df['symbol'].iloc[0]
        # Fetch stock data for the symbol
        stock_data = self.processor.fetch_stock_data(symbol)
        # Check if the returned data is not empty
        self.assertIsNotNone(stock_data, "The returned data should not be empty.")

if __name__ == "__main__":
    unittest.main()
