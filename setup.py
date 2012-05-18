from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='tornadoext',
      version=version,
      description="copy from flask-mongoalchemy",
      long_description="""\
copy from flask-mongoalchemy""",
      classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
      ], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='tornado mongoalchemy',
      author='cloud',
      author_email='cloudcry@gmail.com',
      url='http://www.douban.com/people/no_/',
      license='MIT',
      #packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      packages=['tornadoext', 'tornadoext.mongoalchemy'],
      include_package_data=True,
      namespace_packages=['tornadoext'],
      zip_safe=False,
      install_requires=[
          'tornado>=2.1.1',
          'pymongo>=2.1.1',
          'MongoAlchemy>=0.12'
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
