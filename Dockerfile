# Start with Python 3.10 slim image for a smaller footprint
FROM python:3.10-slim

# Set working directory in the container
WORKDIR /app

# Create a non-root user for security
RUN groupadd -r gradiouser && useradd -r -g gradiouser gradiouser

# Copy requirements file first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set ownership to non-root user
RUN chown -R gradiouser:gradiouser /app

# Switch to non-root user
USER gradiouser

# Expose the port Gradio runs on
EXPOSE 7860

# Set Gradio to listen on all network interfaces
ENV GRADIO_SERVER_NAME="0.0.0.0"

# Command to run the application
CMD ["python", "app.py"] 