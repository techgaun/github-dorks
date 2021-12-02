from setuptools import setup

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='github-dorks',
    version='0.1',
    description='Find leaked secrets via github search.',
    license='Apache License 2.0',
    long_description=long_description,
    author='Samar Dhwoj Acharya (@techgaun)',
    long_description_content_type='text/markdown',
    scripts=['github-dork.py'],
    data_files=[('github-dorks', ['github-dorks.txt'])],
    install_requires=[
        'github3.py==1.0.0a2',
        'feedparser==6.0.2',
    ],
)
