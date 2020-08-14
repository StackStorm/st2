from __future__ import absolute_import
import os.path

from setuptools import setup
from setuptools import find_packages

from dist_utils import fetch_requirements
from dist_utils import apply_vagrant_workaround

from mock_query_callback import __version__

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_FILE = os.path.join(BASE_DIR, 'requirements.txt')

install_reqs, dep_links = fetch_requirements(REQUIREMENTS_FILE)

apply_vagrant_workaround()
setup(
    name='stackstorm-runner-mock_query_callback',
    version=__version__,
    description=('Mock runner for query callback'),
    author='StackStorm',
    author_email='info@stackstorm.com',
    license='Apache License (2.0)',
    url='https://stackstorm.com/',
    install_requires=install_reqs,
    dependency_links=dep_links,
    test_suite='tests',
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['setuptools', 'tests']),
    package_data={'mock_query_callback': ['runner.yaml']},
    scripts=[],
    entry_points={
        'st2common.runners.runner': [
            'mock_query_callback = mock_query_callback.mock_query_callback',
        ],
        'st2common.runners.query': [
            'mock_query_callback = mock_query_callback.query',
        ],
        'st2common.runners.callback': [
            'mock_query_callback = mock_query_callback.callback',
        ],
    }
)
