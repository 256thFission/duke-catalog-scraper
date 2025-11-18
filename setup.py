from setuptools import setup, find_packages

setup(
    name="duke-catalog-scraper",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "duke-sso-auth @ git+https://github.com/256thFission/duke-sso-auth.git",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.8",
    description="A utility to scrape course data from DukeHub",
    author="Duke Student",
    license="MIT",
)
