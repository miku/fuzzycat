import setuptools

from fuzzycat import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

    setuptools.setup(
        name="fuzzycat",
        version=__version__,
        author="Martin Czygan",
        author_email="martin@archive.org",
        description="Fuzzy matching utilities for scholarly metadata",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://github.com/miku/fuzzycat",
        packages=setuptools.find_packages(),
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
        ],
        python_requires=">=3.6",
        zip_safe=False,
        entry_points={"console_scripts": [
            "fuzzycat=fuzzycat:__main__"
        ]},
        install_requires=[
            "dynaconf>=3",
             "elasticsearch-dsl>=7.0.0,<8.0.0",
            "fatcat-openapi-client>=0.3.3", # https://pypi.org/project/fatcat-openapi-client/
            "ftfy",
            "glom",
            "jellyfish",
            "regex",
            "requests>=2",
            "toml",
            "unidecode>=0.10",
            "zstandard",
        ],
        extras_require={"dev": [
            "ipython",
            "isort",
            "mypy",
            "pylint",
            "pytest",
            "pytest-cov",
            "twine",
            "yapf",
        ],},
    )
