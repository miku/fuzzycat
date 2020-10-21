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
            "fuzzycat-cluster=fuzzycat.cluster:main",
        ],},
        install_requires=[
            "elasticsearch>=7",
            "fatcat-openapi-client",
            "ftfy",
            "fuzzy",
            "simhash",
            "toml",
            "unidecode>=0.10",
        ],
        extras_require={"dev": [
            "ipython",
            "isort",
            "jupyter",
            "matplotlib",
            "pandas",
            "pylint",
            "pytest",
            "pytest-cov",
            "twine",
            "yapf",
        ],},
    )
