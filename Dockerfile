# Use an official Python runtime as the base image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the necessary files into the container
COPY operator/ /app/operator/
COPY config/ /app/config/
COPY setup.py /app/
COPY setup.cfg /app/
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

# Set the entrypoint command
CMD [ "kopf", "run", "operator/__init__.py" ]

