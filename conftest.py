# TensorFlow 2.16 imports ``distutils``, which Python 3.12 removed from the
# standard library. Importing setuptools here (before pytest collects any test
# module that pulls in TensorFlow) activates setuptools' distutils shim. The
# startup ``.pth`` hook that normally does this doesn't reliably apply under the
# pytest entry point, so we do it explicitly.
import setuptools  # noqa: F401
