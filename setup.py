"""Setup script for Receipt Checker"""

from setuptools import setup, find_packages

setup(
    name="receipt-checker",
    version="0.1.0",
    description="Match bank statement transactions with receipt PDFs",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "PyPDF2>=3.0.1",
        "pdfplumber>=0.10.3",
        "pandas>=2.1.4",
        "openpyxl>=3.1.2",
        "fuzzywuzzy>=0.18.0",
        "python-Levenshtein>=0.23.0",
        "click>=8.1.7",
        "rich>=13.7.0",
    ],
    entry_points={
        'console_scripts': [
            'receipt-checker=main:cli',
        ],
    },
    python_requires='>=3.8',
)
