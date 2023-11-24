import setuptools

setuptools.setup(
    name="k8s-iam-operator",
    version="1.0.0",
    author="Yannick Siewe",
    author_email="yannick.siewe@gmail.com",
    description="This Kubernetes operator purpose is to facilitate user management in kubernetes base on RBAC",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        'kopf>=1.34.0',
        'kubernetes>=21.0.0',
        'flask>=1.1.2',
        'flask_monitoringdashboard>=1.0.0',
        'gunicorn>=20.1.0',
        'numpy>=1.21.0',
        'opentracing>=2.4.0',
        'jaeger-client>=4.6.0',
        'flask_opentracing>=0.4.0',
        'prometheus_client>=0.11.0',
        'requests>=2.25.1',
        'pyyaml>=5.4.1',
        'opentelemetry-api>=1.4.0',
        'opentelemetry-sdk>=1.4.0',
        'opentelemetry-instrumentation>=0.24b0',
        'opentelemetry-exporter-jaeger>=1.4.0',
        'opentelemetry-exporter-otlp>=1.4.0',
    ],
    entry_points={
        'console_scripts': [
            'k8s-iam-operator = operator_core.__main__:main',
        ],
    },
)