from setuptools import setup, find_packages
from os import path


here = path.abspath(path.dirname(__file__))


# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="synapsesync",  # Required
    version="0.0.2",  # Required
    description="Sync files or hyperlinks to a Synapse project",  # Optional
    long_description=long_description,  # Optional
    long_description_content_type="text/markdown",  # Optional (see note above)
    url="https://github.com/zdk123/SynapseSync",  # Optional
    author="Zachary D. Kurtz",  # Optional
    author_email="zdkurtz@gmail.com",  # Optional
    packages=find_packages(),  # Required
    package_dir={"synapsesync": "synapsesync"},
    package_data={"synapsesync": ["*"]},
    include_package_data=True,
    python_requires=">=3.5",
    install_requires=[
        "synapseclient",
        "pydrive",
        "treelib",
        "requests",
        "prov",
        "typing",
        "pydot",
    ],  # Optional
    # project_urls={  # Optional
    #     "Bug Reports": "https://github.com/zdk123/SynapseSync/issues",
    #     "Source": "https://github.com/zdk123/SynapseSync",
    # },
)
