# Dockerfile for Email Parsing MCP Server

# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY src/ ./src/

# Set the PYTHONPATH to include the app directory
ENV PYTHONPATH=/app

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable for the port (optional, as config.py has a default)
ENV APP_PORT=8000

# Run webhook.py when the container launches
# The application is served by uvicorn, targeting the 'app' instance in 'src.webhook'
CMD ["uvicorn", "src.webhook:app", "--host", "0.0.0.0", "--port", "8000"]
