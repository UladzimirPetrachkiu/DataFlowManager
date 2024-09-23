# main.py

import multiprocessing
import argparse
from prefect import flow
from src.bot import run_bot
from src.flow import run_stock_data_flow

# Define the Flow with a decorator
@flow(name="Stock Data Flow")
def stock_data_flow(csv_file: str):
    # Start the Telegram bot process
    bot_process = multiprocessing.Process(target=run_bot)
    bot_process.daemon = True
    bot_process.start()

    # Start the stock data flow process
    flow_process = multiprocessing.Process(target=run_stock_data_flow, args=(csv_file,))
    flow_process.start()

    # Wait for the flow process to finish
    flow_process.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Data Flow Manager.")
    parser.add_argument("csv_file", type=str, help="Path to the CSV file.")
    args = parser.parse_args()

    # Pass csv_file to the flow
    stock_data_flow(args.csv_file)
