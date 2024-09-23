# src/flow.py

import asyncio
import requests
import pandas as pd
import matplotlib

from typing import Dict, Any
from pathlib import Path

import time
import psutil
import os

import concurrent.futures

from datetime import timedelta

from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from prefect.artifacts import create_markdown_artifact

from src.bot import telegram_bot
from src.config import (
    API_KEY, API_URL, RATE_LIMIT_INTERVAL, USE_SEMAPHORE, WORKER_SEMAPHORE,
    INITIAL_WORKERS, MAX_WORKERS, RETRIES, RETRY_DELAY_SECONDS,
    CPU_LOAD_THRESHOLD, MEMORY_USAGE_THRESHOLD
)

# Set Matplotlib backend to avoid GUI warning
matplotlib.use('Agg')

class StockDataProcessor:
    """Class for processing stock data: reading CSV, fetching data from API, processing
    data, and saving it as JSON."""

    def __init__(self, api_key: str, api_url: str) -> None:
        """
        Initializes the StockDataProcessor with the given API key and URL.

        Args:
            api_key (str): The API key for accessing the stock data.
            api_url (str): The URL for the stock data API.
        """
        self.api_key = api_key
        self.api_url = api_url
        self.rate_limit_interval = RATE_LIMIT_INTERVAL
        self._last_request_time = 0  # Initialize last request time

    @task(
        retries=RETRIES,
        retry_delay_seconds=RETRY_DELAY_SECONDS,
        name="Read CSV",
        cache_key_fn=task_input_hash,
        cache_expiration=timedelta(minutes=5),
    )
    def read_csv(self, file_path: str) -> pd.DataFrame:
        """
        Reads data from a CSV file.

        Args:
            file_path (str): The path to the CSV file.

        Returns:
            pd.DataFrame: The data read from the CSV file.
        """
        logger = get_run_logger()
        try:
            df = pd.read_csv(file_path, sep=";")
            logger.info(f"CSV file loaded: {file_path}")
            return df
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            raise

    @task(
        retries=RETRIES,
        retry_delay_seconds=RETRY_DELAY_SECONDS,
        name="Fetch Stock Data",
        tags=["api"],
        cache_key_fn=task_input_hash,
        cache_expiration=timedelta(hours=1),
    )
    def fetch_stock_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches stock data from the Alpha Vantage API.

        Args:
            symbol (str): The stock symbol to fetch data for.

        Returns:
            Dict[str, Any]: The stock data returned by the API.
        """
        logger = get_run_logger()
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": self.api_key,
        }

        if USE_SEMAPHORE:
            with WORKER_SEMAPHORE:
                current_time = time.time()
                time_since_last_request = current_time - self._last_request_time
                if time_since_last_request < self.rate_limit_interval:
                    sleep_time = self.rate_limit_interval - time_since_last_request
                    logger.info(
                        f"Rate limiting in effect. Sleeping for {sleep_time:.2f} seconds before "
                        f"requesting {symbol}."
                    )
                    time.sleep(sleep_time)
                self._last_request_time = time.time()

        try:
            response = requests.get(self.api_url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error fetching data for {symbol}: {response.text}")
                if response.status_code == 429:  # Too Many Requests
                    raise Exception("Rate limit exceeded. Deferring task.")
                else:
                    raise Exception(f"API request failed with status code {response.status_code}")
        except Exception as e:
            logger.error(f"Exception occurred when fetching data for {symbol}: {e}")
            raise

    @task(
        retries=RETRIES,
        retry_delay_seconds=RETRY_DELAY_SECONDS,
        name="Process Stock Data",
        cache_key_fn=task_input_hash,
        cache_expiration=timedelta(hours=1),
    )
    def process_stock_data(self, data: Dict[str, Any], symbol: str) -> pd.DataFrame:
        """
        Processes API stock data into a DataFrame.

        Args:
            data (Dict[str, Any]): The stock data returned by the API.
            symbol (str): The stock symbol.

        Returns:
            pd.DataFrame: The processed stock data.
        """
        logger = get_run_logger()
        time_series = data.get("Time Series (Daily)", {})
        if time_series:
            df = pd.DataFrame.from_dict(time_series, orient="index")
            df.columns = ["open", "high", "low", "close", "volume"]
            df = df.apply(pd.to_numeric, errors='coerce')
            df.index = pd.to_datetime(df.index)
            logger.info(f"Processed data: {len(df)} rows for {symbol}")

            # Generate visualization using Prefect artifacts
            plot = df['close'].plot(title=f"Closing Prices for {symbol}")
            fig = plot.get_figure()
            output_dir = Path("output_data/plot")
            output_dir.mkdir(parents=True, exist_ok=True)
            symbol_lowercase = symbol.lower()
            plot_path = output_dir / f"{symbol_lowercase}_plot.png"
            fig.savefig(plot_path)
            markdown_content = f"## {symbol} Closing Prices\n![{symbol} Closing Prices]({plot_path})"
            create_markdown_artifact(key=f"{symbol_lowercase}-closing-prices", markdown=markdown_content)
            logger.info(f"Generated plot for {symbol}")

            return df
        else:
            logger.warning(f"No data available for the stock {symbol}.")
            return pd.DataFrame()

    @task(
        retries=RETRIES,
        retry_delay_seconds=RETRY_DELAY_SECONDS,
        name="Save to JSON",
    )
    def save_to_json(self, df: pd.DataFrame, symbol: str) -> None:
        """
        Saves DataFrame to JSON format.

        Args:
            df (pd.DataFrame): The DataFrame to save.
            symbol (str): The stock symbol.
        """
        logger = get_run_logger()
        output_dir = Path("output_data/json")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{symbol}_stock_data.json"
        try:
            df.to_json(output_path, orient="records", indent=4, date_format='iso')
            logger.info(f"Data saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving data to JSON: {e}")
            raise

    @task(name="Send Notification")
    def send_notification(self, message: str) -> None:
        """
        Sends a notification via Telegram.

        Args:
            message (str): The message to be sent as a notification.
        """
        logger = get_run_logger()
        try:
            asyncio.run(telegram_bot.send_notification(message))
            logger.info("Notification sent via Telegram.")
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")

    @task
    def process_symbol(self, symbol: str) -> str:
        """
        Processes a single stock symbol.

        Args:
            symbol (str): The stock symbol to process.

        Returns:
            str: The processed stock symbol.
        """
        logger = get_run_logger()
        try:
            # Fetch stock data
            stock_data = self.fetch_stock_data(symbol)
            # Process stock data
            processed_data = self.process_stock_data(stock_data, symbol)
            # Save to JSON
            self.save_to_json(processed_data, symbol)
            return symbol
        except Exception as e:
            logger.error(f"Error processing symbol {symbol}: {e}")
            raise Exception(symbol) from e

    def adjust_executor_workers(self, executor: concurrent.futures.ThreadPoolExecutor,
                                pending_tasks: int, initial_workers: int, max_workers: int,
                                logger: Any) -> concurrent.futures.ThreadPoolExecutor:
        """
        Adjusts the number of workers based on system load and pending tasks.

        Args:
            executor (concurrent.futures.ThreadPoolExecutor): The current executor.
            pending_tasks (int): The number of pending tasks.
            initial_workers (int): The initial number of workers.
            max_workers (int): The maximum number of workers.
            logger (Any): The logger instance.

        Returns:
            concurrent.futures.ThreadPoolExecutor: The adjusted executor.
        """
        cpu_load = psutil.cpu_percent(interval=1)  # Get current CPU load
        memory_usage = psutil.virtual_memory().percent  # Get current memory usage

        # Increase workers if system load is below thresholds
        if cpu_load < CPU_LOAD_THRESHOLD and memory_usage < MEMORY_USAGE_THRESHOLD:
            desired_workers = min(max_workers, max(initial_workers, pending_tasks // 2))
        else:
            # Reduce workers when system resources are under heavy use
            desired_workers = max(initial_workers, executor._max_workers - 1)

        # Adjust if the desired number of workers is different
        if executor._max_workers != desired_workers:
            logger.info(
                f"Adjusting workers from {executor._max_workers} to {desired_workers} "
                f"based on system load (CPU: {cpu_load}%, Memory: {memory_usage}%)"
            )
            executor.shutdown(wait=False)  # Shutdown current executor
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=desired_workers)

        return executor

def stock_data_flow(csv_file_path: str) -> None:
    """
    Main Prefect flow orchestrating CSV reading, API requests, data processing, and result saving.

    Args:
        csv_file_path (str): The path to the CSV file.
    """
    logger = get_run_logger()
    os.environ["OMP_NUM_THREADS"] = "1"  # Limit CPU usage
    processor = StockDataProcessor(api_key=API_KEY, api_url=API_URL)

    # Step 1: Read CSV file
    df = processor.read_csv(file_path=csv_file_path)

    # Step 2: Get list of symbols
    symbols = df["symbol"].tolist()

    # Step 3: Set up dynamic executor
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=INITIAL_WORKERS)
    futures = []

    # Initialize variables for dynamic scaling
    pending_tasks = len(symbols)
    completed_tasks = 0

    try:
        for symbol in symbols:
            # Adjust the number of workers dynamically based on pending tasks
            executor = processor.adjust_executor_workers(executor, pending_tasks,
                                                         INITIAL_WORKERS, MAX_WORKERS, logger)
            future = executor.submit(processor.process_symbol, symbol)
            futures.append(future)
            pending_tasks -= 1

        # Collect results and handle exceptions
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result:
                    completed_tasks += 1
                    logger.info(f"Completed processing for symbol: {result}")
            except Exception as e:
                logger.error(f"Task resulted in an exception: {e}")
                if "Rate limit exceeded" in str(e):
                    logger.info("Deferring task due to rate limit.")
                    time.sleep(processor.rate_limit_interval)
                    deferred_future = executor.submit(processor.process_symbol, result)
                    futures.append(deferred_future)
                else:
                    logger.error(f"Failed to process symbol due to error: {e}")
    finally:
        executor.shutdown()

    # Step 4: Send completion notification
    processor.send_notification(f"Stock data processing completed. {completed_tasks} tasks completed.")

def run_stock_data_flow(csv_file: str) -> None:
    """
    Function to run the stock data flow.

    Args:
        csv_file (str): The path to the CSV file.
    """
    stock_data_flow(csv_file)
