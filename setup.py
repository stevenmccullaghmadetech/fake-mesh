#!/usr/bin/env python

from setuptools import setup, find_packages
from os.path import dirname, join

with open(join(dirname(__file__), 'README.md')) as f:
    long_description = f.read()

setup(
    name='Fake Mesh',
    version='0.1.7',
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
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    license='MIT',
    python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*',
    entry_points={
        'console_scripts': ['fake_mesh_server=fake_mesh.server:main']
    },
    classifiers=[
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9'
    ]
)
