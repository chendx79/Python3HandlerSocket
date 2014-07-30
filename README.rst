====
pyhs
====

Overview
--------

pyhs (python-handler-socket) is a Python client library for the
`HandlerSocket <https://github.com/ahiguti/HandlerSocket-Plugin-for-MySQL/>`_
MySQL plugin.

Installation
------------

First, install MySQL and HandlerSocket. Some of the client's functionality
depends on latest revisions of the plugin so keep it up to date.

After that, get the distribution::
    
    pip install python-handler-socket

Or get the package from latest source::

    pip install hg+http://bitbucket.org/excieve/pyhs#egg=python-handler-socket

Or clone the main repository and install manually::

    hg clone http://bitbucket.org/excieve/pyhs
    cd pyhs
    python setup.py install

Check your installation like this::

    python
    >>> from pyhs import __version__
    >>> print __version__

Usage
-----

Usage cases, details and API reference are available
in ``docs`` directory inside the package or
`online <http://python-handler-socket.readthedocs.org/>`_ on RTD.

Changelog
---------

0.2.4
~~~~~
- Fixed infinite loop caused by remotely closed connection.
- Fixed incorrect Unicode chars escaping/unescaping in C speedups.
- Fixed indexes and caches might not be cleaned on connection errors.
- Somewhat refactored error recovery code.

0.2.3
~~~~~
- Fixed single result single-column responses. Fixes issue #1 for real now, I hope.

0.2.2
~~~~~
- Fixed incorrect behavior with single columns responses.
- Changed return value of ``find_modify`` calls with ``return_original=True`` to a list of rows of (field, value) tuples instead of a flat list of values.

0.2.1
~~~~~
- Implemented optimised C versions of ``encode`` and ``decode``.
- Modified installation script to include optional building of C speedups module.

0.2.0
~~~~~
- Added "incr" and "decr" operations support to the ``find_modify`` call.
- Added increment and decrement methods to the ``Manager`` class.
- Added original value result for all ``find_modify`` operations.
- Optimised query string encoding function.

0.1.0
~~~~~
- Initial release.

License
-------

| pyhs is released under MIT license.
| Copyright (c) 2010 Artem Gluvchynsky <excieve@gmail.com>

See ``LICENSE`` file inside the package for full licensing information.
