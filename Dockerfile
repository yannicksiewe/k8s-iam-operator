# Use an official Python runtime as the base image.
# 3.12: 3.9 is EOL, and the urllib3 security pin (>=2.7.0) requires Python >=3.10.
# CI already runs the test suite on 3.11, so 3.12 is well within support.
FROM python:3.12-alpine

# Patch OS packages to pull security fixes present in the base image
# (e.g. musl-utils, zlib) before installing anything else.
RUN apk --no-cache upgrade

# Install build dependencies and libstdc++
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    make \
    g++ \
    && apk add libstdc++

# Set the working directory in the container
WORKDIR /operator_core

# Copy the necessary files into the container
COPY app/ /operator_core/app
COPY setup.py /operator_core/
COPY setup.cfg /operator_core/
COPY requirements.txt /operator_core/

# Upgrade pip, setuptools, and wheel, and install dependencies from requirements.txt
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Remove build dependencies to reduce container size
RUN apk del .build-deps

# Create non-root user for running the operator
RUN adduser -D -u 1000 operator

EXPOSE 8081

# Switch to non-root user
USER operator

# Set the entrypoint command
CMD ["python3", "-m", "app"]
