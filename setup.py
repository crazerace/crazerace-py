# Standard library
from setuptools import setup, find_packages

setup(
    name="crazerace",
    version="0.9.0",
    packages=find_packages(exclude=["test*"]),
    include_package_data=True,
    install_requires=[
        "Flask==1.1.1",
        "PyJWT==1.7.1",
        "prometheus_client==0.7.1",
        "requests==2.31.0",
    ],
)
