import os
from setuptools import setup, find_packages

setup(
    name='gitbi',
    version='0.1.1',
    packages=find_packages(exclude=('example', 'example.*')),
    install_requires=[
    ],
    author='Reuven Peleg',
    author_email='your.email@example.com',
    description='A tool for automating git bisect operations',
    long_description=open('README.md', 'r', encoding='utf-8').read() if os.path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    url='https://github.com/R-Peleg/python_git_bisector',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)