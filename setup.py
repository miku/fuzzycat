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
            "fuzzycat=fuzzycat.fatcat.main:main",
            "fuzzycat-issn=fuzzycat.issn:main",
            "fuzzycat-cluster=fuzzycat.cluster:main",
        ],},
        install_requires=[
            "fatcat-openapi-client",
            "ftfy",
            "simhash",
            "unidecode>=0.10",
            "toml",
            "elasticsearch>=7",
        ],
        extras_require={"dev": [
            "ipython",
            "isort",
            "pylint",
            "jupyter",
            "matplotlib",
            "pandas",
            "pytest",
            "pytest-cov",
            "twine",
            "yapf",
        ],},
    )
