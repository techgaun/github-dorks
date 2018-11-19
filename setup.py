import io
import os
import re

from setuptools import find_packages
from setuptools import setup


def read(filename):
    filename = os.path.join(os.path.dirname(__file__), filename)
    text_type = type(u"")
    with io.open(filename, mode="r", encoding='utf-8') as fd:
        return re.sub(text_type(r':[a-z]+:`~?(.*?)`'), text_type(r'``\1``'), fd.read())


setup(
    name="Github-dork",
    version="0.1.0",
    url="https://github.com/grofers/github-dorks",
    license='MIT',

    author="Avinash Jain",
    author_email="avinashjain030193@gmail.com",

    description="Github-dork is a tool to scan repositories for various credentials.",
    long_description=read("README.rst"),

    #packages=find_packages(exclude=('tests',)),
    #py_modules=['mypackage'],

     entry_points={
         'console_scripts': ['github-dorks=githubdork.test_secrets:main'],
     },
    install_requires=["boto==2.39.0","nose2==0.6.4","python-nmap==0.6.0","requests==2.10.0","github3.py==1.0.0a2","feedparser==5.1.3","unittest2==1.1.0"],

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)


