# Standard library
from setuptools import setup, find_packages

setup(
    name="crazerace",
    version="0.5.1",
    packages=find_packages(exclude=["test*"]),
    include_package_data=True,
    install_requires=["Flask==1.0.2", "PyJWT==1.7.1"],
)
