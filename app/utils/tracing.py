import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_tracer():
    #     # Get the URL from the environment variable
    tempo_endpoint = os.getenv("TEMPO_ENDPOINT", "http://192.168.64.9:4317/")

    # Set up a TracerProvider
    trace.set_tracer_provider(TracerProvider(resource=Resource(attributes={"service.name": "k8s-iam-operator"})))

    # Create an OTLP exporter
    otlp_exporter = OTLPSpanExporter(endpoint=tempo_endpoint, insecure=True)

    # Create a BatchSpanProcessor and add the exporter to it
    span_processor = BatchSpanProcessor(otlp_exporter)

    # Configure the TracerProvider to use the OTLP exporter
    trace.get_tracer_provider().add_span_processor(span_processor)

    tracer = trace.get_tracer(__name__)
    return tracer
