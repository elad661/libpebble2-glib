from setuptools import setup
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(name='libpebble2-glib',
      version='0.1.0',
      packages=['libpebble2_glib'],
      install_requires=requirements)

