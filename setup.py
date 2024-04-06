from setuptools import setup, find_packages

setup(
    name='facespace',
    version='0.1.2',
    author='Automa',
    author_email='facespace@automa.one',
    description='A client for FaceSpace API services',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://vision.automa.one',
    packages=find_packages(),
    install_requires=[
        'requests',
        'python-dateutil',
        'urllib3',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
)
