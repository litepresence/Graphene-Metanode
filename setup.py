import pathlib
from setuptools import setup, find_packages

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

setup(
    name="metanode",
    version="1.0.6",
    description="metanode = GrapheneTrustlessClient()",
    long_description=README,
    long_description_content_type='text/markdown',
    url="https://github.com/litepresence/Graphene-Metanode",
    author="litepresence",
    author_email="finitestate@tutamail.com",
    packages=["metanode"],
    install_requires=["websocket-client >= 1.2.3", "requests", "secp256k1 <= 0.13.2", "ecdsa==0.17.0"],
    include_package_data=True,
    license='MIT',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)
