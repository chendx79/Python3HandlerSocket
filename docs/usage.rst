Usage
=====

Overview
--------

Once the package is correctly installed and HandlerSocket plugin is loaded in
your MySQL instance, you're ready to do some code.

The client consists of two parts: *high level* and *low level*.

In most cases you'll only need the high level part which is handled by
:class:`.manager.Manager` class. It saves developer from index id allocation
and reader, writer server pools management - just provides a simple interface
for all supported operations.

One might want to use the low level interface in case more control over mentioned
things is needed. This part is handled by :class:`.sockets.ReadSocket` and
:class:`.sockets.WriteSocket` for read and write server pools/operations correspondingly.
They both subclass :class:`.sockets.HandlerSocket` which defines the pool and
common operations like opening an index. There's also the :class:`.sockets.Connection`
which controls low-level socket operations and is managed by the pool.

Usage examples
--------------

A few simple snippets of both low and high level usage to get started.

High level
~~~~~~~~~~

This one initialises HandlerSocket connection and inserts a row in a table::

    from pyhs import Manager

    # This will initialise both reader and writer connections to the default hosts
    hs = Manager()

    try:
        # Insert a row into 'cars.trucks' table using default (primary) index
        hs.insert('cars', 'trucks', [('id', '1'), ('company', 'Scania'), ('model', 'G400')])
    except OperationalError, e:
        print 'Could not insert because of "%s" error' % str(e)
    except ConnectionError, e:
        print 'Unable to perform operation due to a connection error. Original error: "%s"' % str(e)

.. note::
    Look how the data is passed - it is a list of field-value pairs. Make sure that
    all values are strings.

Now let's get that data back::

    from pyhs import Manager

    hs = Manager()

    try:
        data = hs.get('cars', 'trucks', ['id', 'company', 'model'], '1')
        print dict(data)
    except OperationalError, e:
        print 'Could not get because of "%s" error' % str(e)
    except ConnectionError, e:
        print 'Unable to perform operation due to a connection error. Original error: "%s"' % str(e)

.. note::
    :meth:`~.manager.Manager.get` is a wrapper over :meth:`~.manager.Manager.find`.
    It only fetches one row searched for by a single comparison value and uses only
    primary index for this. For more complex operations please use ``find``.
    Make sure that the first field in the fields list is the one that is searched
    by and that the list is ordered in the same way fields are present in the index.

    ``find`` and ``get`` return list of field-value pairs as result.

A more complex ``find`` request with composite index and custom servers::

    from pyhs import Manager

    # When several hosts are available, client code will try to use both of them
    # to balance the load and will retry requests in case of failure on one of them.
    read_servers = [('inet', '1.1.1.1', 9998), ('inet', '2.2.2.2', 9998)]
    write_servers = [[('inet', '1.1.1.1', 9999), ('inet', '2.2.2.2', 9999)]]
    hs = Manager(read_servers, write_servers)

    try:
        # This will fetch maximum of 10 rows with 'id' >= 1 and company >= 'Scania'.
        # Unfortunately, HandlerSocket doesn't support multiple condition operations
        # on a single request.
        data = hs.find('cars', 'trucks', '>=', ['id', 'company', 'model'], ['1', 'Scania'], 'custom_index_name', 10)
        # Return value is a list of rows, each of them is a list of (field, value) tuples.
        print [dict(row) for row in data]
    except OperationalError, e:
        print 'Could not find because of "%s" error' % str(e)
    except ConnectionError, e:
        print 'Unable to perform operation due to a connection error. Original error: "%s"' % str(e)

.. note::
    Fields and condition values must be ordered in the same way as present in
    the index (in case it's composite). All fields that aren't in the index
    may be ordered randomly.

    Another important thing is the ``limit`` parameter. In case multiple results
    are expected to be returned by the database, this must be set explicitly.
    HandlerSocket will **not** return all of them by default.

A sample of increment operation with original value returned as result. Similar one exists for decrement.::

    from pyhs import Manager

    hs = Manager()

    try:
        # "incr" increments a numeric value by defined step parameter. By default it is '1'.
        original = hs.incr('cars', 'trucks', '=', ['id'], ['1'], return_original=True)
        print original
        # This will return ['1'] but the new value would be ['2']
    except OperationalError, e:
        print 'Could not find because of "%s" error' % str(e)
    except ConnectionError, e:
        print 'Unable to perform operation due to a connection error. Original error: "%s"' % str(e)

Low level
~~~~~~~~~

A small overview of how to operate HandlerSocket.
An opened index is required to perform any operation. To do this, use
:meth:`.sockets.HandlerSocket.get_index_id` which will open the index and
return its ``id``.

.. note::
    Id's are cached internally by the client and it will return existing id
    (without opening a new index) in case same ``db``, ``table`` and list of
    ``columns`` is passed.

This ``id`` will must used in all further operations that operate over the same
index and columns.
There are two classes that must be used to perform actual operations:
:class:`.sockets.ReadSocket` for reads and :class:`.socket.WriteSocket` for writes.

An example::

    from pyhs.sockets import ReadSocket

    hs = ReadSocket([('inet', '127.0.0.1', 9998)])

    try:
        index_id = hs.get_index_id('cars', 'trucks', ['id', 'company', 'model'])
        data = hs.find(index_id, '=', ['1'])
        # Data will contain a list of results. Each result is a list of row's values.
        print data
    except OperationalError, e:
        print 'Could not find because of "%s" error' % str(e)
    except ConnectionError, e:
        print 'Unable to perform operation due to a connection error. Original error: "%s"' % str(e)

Exception handling
~~~~~~~~~~~~~~~~~~

There are three exceptions that client may raise:

    :exc:`.exceptions.ConnectionError`
        Something bad happened to HandlerSocket connection. Data could not be sent
        or received. Actual reason will be present in the first exception instance's
        argument. Note that the client may retry operations in case several hosts are defined.
    :exc:`.exceptions.OperationalError`
        Raised when HandlerSocket returned an error. Error code is present in the
        exception instance.
    :exc:`.exceptions.IndexedConnectionError`
        ``ConnectionError`` happened when performing an operation with already
        opened index. High level client uses this to retry whole operation in case
        something correctable failed. Developer might want to use it if low level
        client is used.


.. seealso::

    :doc:`API reference <api/index>`
        Description of all public interfaces provided by both parts of the client
