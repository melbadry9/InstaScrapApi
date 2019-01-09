from setuptools import setup, find_packages

setup(
    name= "InstaScrapApi",
    version= "1.0.0",
    author= "Mohamed Elbadry",
    author_email= "mohamed.sa.elbadry@gmail.com",
    packages= find_packages(),
    install_requires=[
        'requests',
        'tqdm',
        'bs4'
        ]
)
