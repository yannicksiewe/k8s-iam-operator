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
WORKDIR /app

# Copy the necessary files into the container
COPY operator_core/ /app/operator_core/
COPY configs/ /app/configs/
COPY setup.py /app/
COPY setup.cfg /app/
COPY requirements.txt /app/

# Upgrade pip, setuptools, and wheel, and install dependencies from requirements.txt
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Remove build dependencies to reduce container size
RUN apk del .build-deps

EXPOSE 8080

# Set the entrypoint command
#CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "4", "operator_core:main"]
CMD ["python3", "-m", "operator_core"]
