#!/usr/bin/env python

from setuptools import setup, find_packages
from os.path import dirname, join

with open(join(dirname(__file__), 'README.md')) as f:
    long_description = f.read()

setup(
    name='Fake Mesh',
    version='0.1.5',
    description='A fake implementation of NHS Digital MESH, but one that should stand up to modest load',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='James Pickering',
    author_email='james.pickering@airelogic.com',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={'fake_mesh': ['*.pem']},
    install_requires=[
        'cheroot (>= 5.8.3)',
        'lmdb (>= 0.93)',
        'monotonic (>= 1.3)',
        'six (>= 1.10.0)',
        'werkzeug (>= 0.12.2)',
        'wrapt (>= 1.10.11)'
    ],
    license='MIT',
    python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*')
