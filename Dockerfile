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
    && rm -rf /var/lib/apt/lists/*

# Copy project files into the container
COPY . .

# Install required Python packages
RUN pip install --upgrade pip
RUN pip install streamlit pandas sqlalchemy

# Expose Streamlit's default port
EXPOSE 8501

# Define default command to run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
