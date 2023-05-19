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
    ],
)
