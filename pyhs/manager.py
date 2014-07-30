from .sockets import *
from .utils import retry_on_failure


class Manager(object):
    """High-level client for HandlerSocket.

    This should be used in most cases except ones that you need fine-grained
    control over index management, low-level operations, etc.
    For such cases :class:`~.sockets.ReadSocket` and :class:`~.sockets.WriteSocket`
    can be used.
    """

    def __init__(self, read_servers=None, write_servers=None, debug=False):
        """Constructor initializes both read and write sockets.

        :param read_servers: list of tuples that define HandlerSocket read
            instances. See format in :class:`~.HandlerSocket` constructor.
        :type read_servers: list of tuples or None
        :param write_servers: list of tuples that define HandlerSocket write
            instances. Format is the same as in ``read_servers``.
        :type write_servers: list of tuples or None
        :param bool debug: enable debug mode by passing ``True``.
        """
        read_servers = read_servers or [('inet', 'localhost', 9998)]
        write_servers = write_servers or [('inet', 'localhost', 9999)]
        self.read_socket = ReadSocket(read_servers, debug)
        self.write_socket = WriteSocket(write_servers, debug)

    def get(self, db, table, fields, value):
        """A wrapper over :meth:`~.find` that gets a single row with
        a single field look up.

        Returns a list of pairs. First item in pair is field name, second is
        its value.

        If multiple result rows, different comparison operation or
        composite indexes are needed please use :meth:`~.find` instead.

        :param string db: database name.
        :param string table: table name.
        :param list fields: list of table's fields to get, ordered by inclusion
            into the index. First item must always be the look up field.
        :param string value: a look up value.
        :rtype: list of tuples
        """
        data = self.find(db, table, '=', fields, [str(value)])
        if data:
            data = data[0]

        return data

    @retry_on_failure
    def find(self, db, table, operation, fields, values, index_name=None, limit=0, offset=0):
        """Finds rows that meet ``values`` with comparison ``operation``
        in given ``db`` and ``table``.

        Returns a list of lists of pairs. First item in pair is field name,
        second is its value.
        For example, if two rows with two columns each are returned::
        
          [[('field', 'first_row_value'), ('otherfield', 'first_row_othervalue')],
           [('field', 'second_row_value'), ('otherfield', 'second_row_othervalue')]]

        :param string db: database name
        :param string table: table name
        :param string operation: logical comparison operation to use over ``columns``.
            Currently allowed operations are defined in
            :const:`~.sockets.HandlerSocket.FIND_OPERATIONS`. Only one operation
            is allowed per call.
        :param list fields: list of table's fields to get, ordered by inclusion
            into the index.
        :param list values: values to compare to, ordered the same way as items
            in ``fields``.
        :param index_name: name of the index to open, default is ``PRIMARY``.
        :type index_name: string or None
        :param integer limit: optional limit of results. Default is one row.
            In case multiple rows are expected to be returned, ``limit`` must be
            set explicitly, HS wont get all found rows by default.
        :param integer offset: optional offset of rows to search for.
        :rtype: list of lists of tuples
        """
        index_id = self.read_socket.get_index_id(db, table, fields, index_name)
        data = self.read_socket.find(index_id, operation, values, limit, offset)

        if data:
            data = [list(zip(fields, row)) for row in data]

        return data

    @retry_on_failure
    def insert(self, db, table, fields, index_name=None):
        """Inserts a single row into given ``table``.

        :param string db: database name.
        :param string table: table name.
        :param fields: list of (column, value) pairs to insert into the ``table``.
        :type fields: list of lists
        :param index_name: name of the index to open, default is ``PRIMARY``.
        :type index_name: string or None
        :rtype: bool
        """
        keys, values = list(zip(*fields))
        index_id = self.write_socket.get_index_id(db, table, keys, index_name)
        data = self.write_socket.insert(index_id, values)

        return data

    @retry_on_failure
    def update(self, db, table, operation, fields, values, update_values,
               index_name=None, limit=0, offset=0, return_original=False):
        """Update row(s) that meet conditions defined by ``operation``, ``fields``
        ``values`` in a given ``table``.

        :param string db: database name
        :param string table: table name
        :param string operation: logical comparison operation to use over ``columns``.
            Currently allowed operations are defined in
            :const:`~.sockets.HandlerSocket.FIND_OPERATIONS`. Only one operation
            is allowed per call.
        :param list fields: list of table's fields to use, ordered by inclusion
            into the index.
        :param list values: values to compare to, ordered the same way as items
            in ``fields``.
        :param list update_values: values to update, ordered the same way as items
            in ``fields``.
        :param index_name: name of the index to open, default is ``PRIMARY``.
        :type index_name: string or None
        :param integer limit: optional limit of rows. Default is one row.
            In case multiple rows are expected to be updated, ``limit`` must be
            set explicitly, HS wont update all found rows by default.
        :param integer offset: optional offset of rows to search for.
        :param bool return_original: if set to ``True``, method will return a
            list of original values in affected rows. Otherwise - number of
            affected rows (this is default behaviour).
        :rtype: int or list
        """
        index_id = self.write_socket.get_index_id(db, table, fields, index_name)
        op = 'U' + (return_original and '?' or '')
        data = self.write_socket.find_modify(index_id, operation, values, op,
                                             update_values, limit, offset)

        if data:
            data = return_original and [list(zip(fields, row)) for row in data] \
                or int(data[0][0])
        return data
    
    @retry_on_failure
    def incr(self, db, table, operation, fields, values, step=['1'], index_name=None,
               limit=0, offset=0, return_original=False):
        """Increments row(s) that meet conditions defined by ``operation``, ``fields``
        ``values`` in a given ``table``.

        :param string db: database name
        :param string table: table name
        :param string operation: logical comparison operation to use over ``columns``.
            Currently allowed operations are defined in
            :const:`~.sockets.HandlerSocket.FIND_OPERATIONS`. Only one operation
            is allowed per call.
        :param list fields: list of table's fields to use, ordered by inclusion
            into the index.
        :param list values: values to compare to, ordered the same way as items
            in ``fields``.
        :param list step: list of increment steps, ordered the same way as items
            in ``fields``.
        :param index_name: name of the index to open, default is ``PRIMARY``.
        :type index_name: string or None
        :param integer limit: optional limit of rows. Default is one row.
            In case multiple rows are expected to be updated, ``limit`` must be
            set explicitly, HS wont update all found rows by default.
        :param integer offset: optional offset of rows to search for.
        :param bool return_original: if set to ``True``, method will return a
            list of original values in affected rows. Otherwise - number of
            affected rows (this is default behaviour).
        :rtype: int or list
        """
        index_id = self.write_socket.get_index_id(db, table, fields, index_name)
        op = '+' + (return_original and '?' or '')
        data = self.write_socket.find_modify(index_id, operation, values, op,
                                             step, limit, offset)

        if data:
            data = return_original and [list(zip(fields, row)) for row in data] \
                or int(data[0][0])
        return data

    @retry_on_failure
    def decr(self, db, table, operation, fields, values, step=['1'], index_name=None,
               limit=0, offset=0, return_original=False):
        """Decrements row(s) that meet conditions defined by ``operation``, ``fields``
        ``values`` in a given ``table``.

        :param string db: database name
        :param string table: table name
        :param string operation: logical comparison operation to use over ``columns``.
            Currently allowed operations are defined in
            :const:`~.sockets.HandlerSocket.FIND_OPERATIONS`. Only one operation
            is allowed per call.
        :param list fields: list of table's fields to use, ordered by inclusion
            into the index.
        :param list values: values to compare to, ordered the same way as items
            in ``fields``.
        :param list step: list of decrement steps, ordered the same way as items
            in ``fields``.
        :param index_name: name of the index to open, default is ``PRIMARY``.
        :type index_name: string or None
        :param integer limit: optional limit of rows. Default is one row.
            In case multiple rows are expected to be updated, ``limit`` must be
            set explicitly, HS wont update all found rows by default.
        :param integer offset: optional offset of rows to search for.
        :param bool return_original: if set to ``True``, method will return a
            list of original values in affected rows. Otherwise - number of
            affected rows (this is default behaviour).
        :rtype: int or list
        """
        index_id = self.write_socket.get_index_id(db, table, fields, index_name)
        op = '-' + (return_original and '?' or '')
        data = self.write_socket.find_modify(index_id, operation, values, op,
                                             step, limit, offset)

        if data:
            data = return_original and [list(zip(fields, row)) for row in data] \
                or int(data[0][0])
        return data

    @retry_on_failure
    def delete(self, db, table, operation, fields, values, index_name=None,
               limit=0, offset=0, return_original=False):
        """Delete row(s) that meet conditions defined by ``operation``, ``fields``
        ``values`` in a given ``table``.

        :param string db: database name
        :param string table: table name
        :param string operation: logical comparison operation to use over ``columns``.
            Currently allowed operations are defined in
            :const:`~.sockets.HandlerSocket.FIND_OPERATIONS`. Only one operation
            is allowed per call.
        :param list fields: list of table's fields to use, ordered by inclusion
            into the index.
        :param list values: values to compare to, ordered the same way as items
            in ``fields``.
        :param index_name: name of the index to open, default is ``PRIMARY``.
        :type index_name: string or None
        :param integer limit: optional limit of rows. Default is one row.
            In case multiple rows are expected to be deleted, ``limit`` must be
            set explicitly, HS wont delete all found rows by default.
        :param integer offset: optional offset of rows to search for.
        :param bool return_original: if set to ``True``, method will return a
            list of original values in affected rows. Otherwise - number of
            affected rows (this is default behaviour).
        :rtype: int or list
        """
        index_id = self.write_socket.get_index_id(db, table, fields, index_name)
        op = 'D' + (return_original and '?' or '')
        data = self.write_socket.find_modify(index_id, operation, values, op,
                                             limit=limit, offset=offset)

        if data:
            data = return_original and [list(zip(fields, row)) for row in data] \
                or int(data[0][0])
        return data

    def purge(self):
        """Purges all read and write connections.
        All requests after that operation will open new connections, index
        caches will be cleaned too.
        """
        self.read_socket.purge()
        self.write_socket.purge()