# Use Python 3.8 as base - this version has good compatibility with older packages
FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Install git (needed for pip install from git repos)
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy only the necessary files
COPY github-dork.py /app/
COPY github-dorks.txt /app/
COPY setup.py /app/
COPY README.md /app/
COPY requirements.txt /app/

# Install dependencies
# Using the specific version of github3.py that's known to work
RUN pip install --no-cache-dir github3.py==1.0.0a2 feedparser==6.0.2

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# Create volume for potential output files
VOLUME ["/app/output"]

ENTRYPOINT ["python", "github-dork.py"] 