Installation
============

HandlerSocket plugin
--------------------

First, you'll have to get this working. At the moment of writing the only way
to do this, was getting the source code, compiling it and loading into the
MySQL instance. Keep the HandlerSocket up to date as the client gets updated
from time to time as new features or changes appear in the plugin.

.. seealso::

    `Installation guide <https://github.com/ahiguti/HandlerSocket-Plugin-for-MySQL/blob/master/docs-en/installation.en.txt>`_
        HandlerSocket installation guide at the official repository.

The Client
----------

At the moment you can install pyhs by either using `pip <http://pip.openplans.org/>`_,
easy_install, downloading from PyPI or getting source directly from bitbucket.

Pip way
~~~~~~~
This is very simple, just run::

    pip install python-handler-socket

Or this to get the latest (not yet released on PyPI)::

    pip install hg+http://bitbucket.org/excieve/pyhs#egg=python-handler-socket

This command will install the package into your site-packages or dist-packages.

Source
~~~~~~
Clone the source from the repository and install it::

    hg clone http://bitbucket.org/excieve/pyhs
    cd pyhs
    python setup.py install

By default additional C speedups are also built and installed (if possible).
However, if they are not needed, please use ``--without-speedups`` option.

Testing installation
~~~~~~~~~~~~~~~~~~~~

Check your installation by running this in Python interpreter::

    from pyhs import __version__
    print __version__

This should show currently installed version of pyhs.
You're all set now.
