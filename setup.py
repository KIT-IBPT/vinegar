#!/usr/bin/env python3

from setuptools import setup, find_packages

from vinegar.version import VERSION_STRING

setup(
    name="vinegar",
    version=VERSION_STRING,
    packages=find_packages(
        include=['vinegar', 'vinegar.*'],
    ),
    zip_safe=True,

    install_requires=['Jinja2', 'PyYAML'],
    python_requires='>=3.5',

    entry_points={
        'console_scripts': [
            'vinegar-server = vinegar.cli.server:main',
        ],
        'gui_scripts': [
        ]
    },
    test_suite='tests.unit',

    description='Salt-style PXE boot server',
    url='https://www.ibpt.kit.edu/',
)
