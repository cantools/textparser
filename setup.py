#!/usr/bin/env python3

from setuptools import setup
from setuptools import find_packages
import re


def find_version():
    return re.search(r"^__version__ = '(.*)'$",
                     open('textparser.py', 'r').read(),
                     re.MULTILINE).group(1)


setup(name='textparser',
      version=find_version(),
      description='Text parser.',
      long_description=open('README.rst', 'r').read(),
      author='Erik Moqvist',
      author_email='erik.moqvist@gmail.com',
      license='MIT',
      classifiers=[
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3',
      ],
      keywords=['parser', 'parsing'],
      url='https://github.com/eerimoq/textparser',
      py_modules=['textparser'],
      python_requires='>=3.10',
      extras_require={
          "test": [
              "mypy >= 2.1",
              "ruff >= 0.15.12",
          ],
      },
      package_data={
          "textparser": ["py.typed"],
      },
      test_suite="tests")
