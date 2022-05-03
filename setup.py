import os

from setuptools import find_packages, setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='n8n',
    version='0.8.0',
    packages=find_packages(),
    include_package_data=True,
    license='GPLv3',
    url='https://github.com/victorpantoja/n8n-client-python',
    author='Victor Pantoja',
    author_email='victor.pantoja@gmail.com',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
    ],
    install_requires=[
        "requests"
    ],
    long_description=read('README.md'),
    zip_safe=False,
)
