from distutils.core import setup, Extension

pyxpmodule = Extension('pyxp', sources=['pyxp.c'], libraries=['ixp'])

setup(name = 'PYXP',
        version = '0.1',
        description = 'Python extension for libixp',
        ext_modules = [pyxpmodule])
