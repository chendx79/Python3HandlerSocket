.. pyhs documentation master file, created by
   sphinx-quickstart on Sun Nov 28 01:17:44 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pyhs
===============

pyhs is a pure Python client (with optional C speedups) for `HandlerSocket <https://github.com/ahiguti/HandlerSocket-Plugin-for-MySQL>`_
plugin to MySQL database. In short, it provides access to the data omitting
the SQL engine in a NoSQL-like interface. It allows all simple operations
(get, insert, update, delete) over indexed data to perform considerably faster
than by usual means.

See `this <http://yoshinorimatsunobu.blogspot.com/2010/10/using-mysql-as-nosql-story-for.html>`_
article for more details about HandlerSocket.

This client supports both read and write operations but no batching at the moment.

Go to :doc:`installation` and :doc:`usage` sections for quick start. There's also a
:doc:`reference <api/index>` for all public interfaces.

Project is open-source and always available on the bitbucket:
http://bitbucket.org/excieve/pyhs/


Contents:

.. toctree::
   :maxdepth: 2

   installation
   usage
   api/index
