# src/config.py

import os
from dotenv import load_dotenv
from threading import Semaphore

# Load environment variables from .env file
load_dotenv()

# API Configuration
API_KEY = os.getenv("API_KEY", "demo")
API_URL = os.getenv("API_URL", "https://www.alphavantage.co/query")

# Rate Limiting Configuration
RATE_LIMIT_INTERVAL = int(os.getenv("RATE_LIMIT_INTERVAL", 30))
USE_SEMAPHORE = int(os.getenv("USE_SEMAPHORE", 1))
WORKER_SEMAPHORE = Semaphore(1) if USE_SEMAPHORE else None

# Executor Configuration
INITIAL_WORKERS = int(os.getenv("INITIAL_WORKERS", 2))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 10))

# Retry Configuration
RETRIES = int(os.getenv("RETRIES", 3))
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", 10))

# System Load Thresholds
CPU_LOAD_THRESHOLD = int(os.getenv("CPU_LOAD_THRESHOLD", 75))
MEMORY_USAGE_THRESHOLD = int(os.getenv("MEMORY_USAGE_THRESHOLD", 75))

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
