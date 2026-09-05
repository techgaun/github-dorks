FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy only the files needed to install and run the project
COPY github_dorks /app/github_dorks
COPY github-dorks.txt /app/
COPY pyproject.toml /app/
COPY README.md /app/

RUN pip install --no-cache-dir .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# Create volume for potential output files
VOLUME ["/app/output"]

ENTRYPOINT ["github-dorks"]
