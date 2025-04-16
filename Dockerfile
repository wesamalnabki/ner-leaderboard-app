# Use a slim Python base image
FROM python:3.10-slim

# Set environment variables to improve Python behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better cache use
COPY requirements.txt .

# Install required Python packages
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of the project files into the container
COPY ./src .

# Add Streamlit config
RUN mkdir -p /root/.streamlit
COPY config.toml /root/.streamlit/config.toml

# Expose Streamlit's default port
EXPOSE 8501

# Define default command to run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
