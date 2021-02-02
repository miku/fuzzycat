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
        python_requires=">=3.5",
        zip_safe=False,
        entry_points={"console_scripts": [
            "fuzzycat=fuzzycat"
        ]},
        install_requires=[
            "elasticsearch",
            "elasticsearch-dsl",
            "fatcat-openapi-client", # https://pypi.org/project/fatcat-openapi-client/
            "ftfy",
            "fuzzy",
            "glom",
            "regex",
            "requests",
            "toml",
            "unidecode>=0.10",
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
