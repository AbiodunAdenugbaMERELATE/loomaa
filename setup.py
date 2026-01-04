from pathlib import Path

from setuptools import setup, find_packages


_HERE = Path(__file__).resolve().parent
_LONG_DESCRIPTION = (_HERE / "README.md").read_text(encoding="utf-8")

setup(
    name='loomaa',
    version='0.1.1',
    packages=find_packages(),
    install_requires=[
        "typer>=0.9.0",
        "pydantic>=2.0.0",
        "jinja2>=3.1.0",
        "requests>=2.31.0",
        "msal>=1.27.0",
        "streamlit>=1.28.0",
        "plotly>=5.17.0",
        "networkx>=3.2.0", 
        "pandas>=2.0.0",
    ],
    entry_points={
        'console_scripts': [
            'loomaa=loomaa._bootstrap:main',
        ],
    },
    author='Abiodun Adenugba',
    description='DevOps-native semantic model compiler for Microsoft Fabric',
    long_description=_LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    license='Apache-2.0',
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
