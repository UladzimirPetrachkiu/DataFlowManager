# Data Flow Manager

Data Flow Manager is a project that processes stock data using Prefect flows and sends notifications to subscribed users via a Telegram bot.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Docker](#docker)
- [Testing](#testing)
- [License](#license)
- [Solution Architecture](#solution-architecture)
- [Configuration Files](#configuration-files)

## Installation

1. **Clone the repository**:

    ```sh
    git clone https://github.com/UladzimirPetrachkiu/DataFlowManager.git
    cd data_flow_manager
    ```

2. **Create a virtual environment and activate it**:

    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install the required dependencies**:

    ```sh
    pip install -r requirements.txt
    ```

## Configuration

1. **Create a `.env` file** in the root directory of the project based on the `.env_example` file provided.

    ```sh
    cp .env_example .env
    ```

2. **Update the `.env` file** with your API keys and other configuration settings.

    ```plaintext
    # API Configuration
    API_KEY=YOUR_ALPHA_VANTAGE_API_KEY
    API_URL=https://www.alphavantage.co/query

    # Rate Limiting Configuration
    RATE_LIMIT_INTERVAL=30

    # Executor Configuration
    INITIAL_WORKERS=2
    MAX_WORKERS=10

    # Retry Configuration
    RETRIES=3
    RETRY_DELAY_SECONDS=10

    # System Load Thresholds
    CPU_LOAD_THRESHOLD=75
    MEMORY_USAGE_THRESHOLD=75

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN

    # Semaphore Configuration
    USE_SEMAPHORE=1
    ```

## Running the Application

1. **Start the Prefect Server and UI**:

    ```sh
    prefect server start
    ```

2. **Create the work pool**:

    ```sh
    prefect work-pool create "stock-data-pool" --type process
    ```

3. **Deploy the flow**:

    ```sh
    prefect deploy --pool "stock-data-pool" --name "stock-data-flow" "main.py:stock_data_flow"
    ```

4. **Start a worker** in a separate terminal to pull work from the 'stock-data-pool':

    ```sh
    prefect worker start --pool 'stock-data-pool'
    ```

5. **Run the flow**:

    To execute flow runs from this deployment, use the following command:

    ```sh
    prefect deployment run 'Stock Data Flow/stock-data-flow'
    ```

## Docker

1. **Build the Docker image**:

    ```sh
    docker build -t data_flow_manager .
    ```

2. **Run the Docker container**:

    ```sh
    docker run -p 4200:4200 data_flow_manager
    ```

    The Prefect UI will be accessible on port 4200.

## Testing

1. **Run the tests**:

    ```sh
    python -m unittest discover tests
    ```

    This will run the tests located in the `tests` directory.

## License

This project is licensed under the MIT License. See the [LICENSE.md](LICENSE.md) file for details.

## Solution Architecture

### Overview

The Data Flow Manager is designed to process stock data and send notifications to subscribed users via a Telegram bot. The architecture is built using Prefect for orchestrating the data processing flow and a Telegram bot for notifications.

### Components

1. **Telegram Bot**:
    - Manages subscriptions for notifications.
    - Sends welcome messages and handles subscription/unsubscription commands.
    - Uses SQLite to store subscriber information.

2. **Stock Data Processor**:
    - Reads stock symbols from a CSV file.
    - Fetches stock data from the Alpha Vantage API.
    - Processes the data into a DataFrame.
    - Saves the processed data as JSON.
    - Sends notifications via the Telegram bot.

3. **Prefect Flow**:
    - Orchestrates the data processing flow.
    - Manages retries and rate limiting.
    - Adjusts the number of workers based on system load.

### Decisions Made

1. **Worker Limits and Restrictions**:
    - **Initial Workers**: Set to 2 to start with a conservative number of workers.
    - **Max Workers**: Set to 10 to allow scaling up based on the load.
    - **CPU and Memory Thresholds**: Set to 75% to ensure the system does not become overloaded.
    - **Rate Limiting**: Implements a rate limit interval to prevent exceeding API rate limits.
    - **Semaphore**: Used to control concurrent API requests to prevent rate limiting issues.

2. **Retry Configuration**:
    - **Retries**: Set to 3 to handle transient failures.
    - **Retry Delay**: Set to 10 seconds to avoid overwhelming the API with immediate retries.

3. **Dynamic Worker Adjustment**:
    - The number of workers is dynamically adjusted based on the number of pending tasks and system load. This ensures efficient resource utilization and prevents system overload.

By implementing these decisions, the Data Flow Manager aims to provide a robust and scalable solution for processing stock data and sending notifications.

## Configuration Files

### Example Prefect Configuration (`prefect.yaml`)

```yaml
# prefect.yaml

# Prefect Agent Configuration
agents:
  default:
    type: local
    labels: [default]
    concurrency: 5  # Limit on the number of simultaneously running tasks

# Prefect Worker Configuration
workers:
  default:
    type: process
    labels: [default]
    concurrency: 5  # Limit on the number of simultaneously running tasks
    env:
      PREFECT_LOGGING_LEVEL: INFO
    resources:
      memory: 512Mi  # Memory limit for workers
      cpu: 1  # CPU limit for workers

# Prefect UI Configuration
ui:
  apollo:
    url: http://localhost:4200/graphql
  server:
    host: 0.0.0.0
    port: 4200
  database:
    connection_url: sqlite:///prefect.db

# Prefect Server Configuration
server:
  host: 0.0.0.0
  port: 4200
  database:
    connection_url: sqlite:///prefect.db

# Prefect Logging Configuration
logging:
  level: INFO
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
deployments:
- name: stock-data-flow
  version:
  tags: []
  concurrency_limit:
  description:
  entrypoint: main.py:stock_data_flow
  parameters:
    csv_file: input_data/CSV.csv
  work_pool:
    name: stock-data-pool
    work_queue_name:
    job_variables: {}
  enforce_parameter_schema: true
  schedules:
  - cron: 0 0 * * *
    timezone: MSK
    day_or: true
    active: true
    max_active_runs:
    catchup: false
  pull:
  - prefect.deployments.steps.git_clone:
      repository: git@github.com:UladzimirPetrachkiu/DataFlowManager.git
      branch: main
```

### Example Docker Configuration (`prefect.yaml`)

```Dockerfile
# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set the environment variables from the .env file
ENV $(cat .env | xargs)

# Install Prefect Server
RUN pip install prefect-server

# Expose the port for the Prefect UI
EXPOSE 4200

# Command to run the application, create the work pool, deploy the flow, and start the worker
CMD ["sh", "-c", "prefect server start & \
                  prefect work-pool create 'stock-data-pool' --type process && \
                  prefect deploy --pool 'stock-data-pool' --name 'stock-data-flow' 'main.py:stock_data_flow' && \
                  prefect deployment run 'Stock Data Flow/stock-data-flow' && \
                  tail -f /dev/null"]
```
