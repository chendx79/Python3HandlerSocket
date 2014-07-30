from setuptools import setup, Extension, Feature
from distutils.command.build_ext import build_ext
from distutils.errors import CCompilerError, DistutilsExecError,\
    DistutilsPlatformError

# Optional C module building method taken from:
# http://github.com/mitsuhiko/markupsafe/blob/master/setup.py
speedups = Feature(
    'optional C speed-enhancement module',
    standard=True,
    ext_modules = [
        Extension('pyhs._speedups', ['pyhs/_speedups.c']),
    ],
)

ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError)

class BuildFailed(Exception):
    pass


class ve_build_ext(build_ext):
    """This class allows C extension building to fail."""

    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError:
            raise BuildFailed()

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except ext_errors:
            raise BuildFailed()


def run_setup(with_binary):
    features = {}
    if with_binary:
        features['speedups'] = speedups
    setup(
        name = 'python-handler-socket',
        version = __import__('pyhs').__version__,
        url = 'http://bitbucket.org/excieve/pyhs',
        license = 'MIT',
        author = 'Artem Gluvchynsky',
        author_email='excieve@gmail.com',
        packages = ["pyhs"],
        long_description = open('README.rst').read(),
        description = 'HandlerSocket client for Python',
        platforms = 'any',

        classifiers = [
            'Development Status :: 3 - Alpha',
            'Environment :: Console',
            'Environment :: Web Environment',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Topic :: Software Development :: Libraries',
            'Topic :: Database',
        ],

        cmdclass={'build_ext': ve_build_ext},
        features=features,
    )

try:
    run_setup(True)
except BuildFailed:
    print('The C extension could not be compiled, speedups are not enabled.')
    print('Trying to build without C extension now.')
    run_setup(False)
    print('Success.')
