# Use an official Python runtime as the base image
FROM python:3.9-alpine

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

EXPOSE 8081

# Set the entrypoint command
#CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "4", "operator_core:main"]
CMD ["python3", "-m", "app"]
