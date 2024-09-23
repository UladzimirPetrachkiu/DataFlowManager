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
                  prefect work-pool create 'data-pool' --type process && \
                  prefect deploy --pool 'data-pool' --name 'data-flow' 'main.py:data_flow' && \
                  prefect deployment run 'Data Flow/data-flow' && \
                  prefect worker start --pool 'data-pool' && \
                  tail -f /dev/null"]
