import socket
import threading
import time
import random
from itertools import chain

try:
    from _speedups import encode, decode
except ImportError:
    from .utils import encode, decode
from .utils import check_columns
from .exceptions import *



class Connection(object):
    """Single HandlerSocket connection.

    Maintains a streamed socket connection and defines methods to send and
    read data from it.
    In case of failure :attr:`~.retry_time` will be set to the exact time after
    which the connection may be retried to deal with temporary connection issues.
    """

    UNIX_PROTO = 'unix'
    INET_PROTO = 'inet'
    DEFAULT_TIMEOUT = 3
    RETRY_INTERVAL = 30

    def __init__(self, protocol, host, port=None, timeout=None):
        """
        :param string protocol: socket protocol (*'unix'* and *'inet'* are supported).
        :param string host: server host for *'inet'* protocol or socket file path for *'unix'*.
        :param port: server port for *'inet'* protocol connection.
        :type port: integer or None
        :param timeout: timeout value for socket, default is defined in
            :const:`.DEFAULT_TIMEOUT`.
        :type timeout: integer or None
        """
        self.timeout = timeout or self.DEFAULT_TIMEOUT

        self.host = host
        if protocol == self.UNIX_PROTO:
            self.protocol = socket.AF_UNIX
            self.address = self.host
        elif protocol == self.INET_PROTO:
            self.protocol = socket.AF_INET
            if not port:
                raise ValueError('Port is not specified for TCP connection')
            self.address = (self.host, port)
        else:
            raise ValueError('Unsupported protocol')

        self.socket = None
        self.retry_time = 0
        self.debug = False

    def set_debug_mode(self, mode):
        """Changes debugging mode of the connection.
        If enabled, some debugging info will be printed to stdout.

        :param bool mode: mode value
        """
        self.debug = mode

    def connect(self):
        """Establishes connection with a new socket. If some socket is
        associated with the instance - no new socket will be created.
        """
        if self.socket:
            return

        try:
            sock = socket.socket(self.protocol, socket.SOCK_STREAM)
            # Disable Nagle algorithm to improve latency:
            # http://developers.slashdot.org/comments.pl?sid=174457&threshold=1&commentsort=0&mode=thread&cid=14515105
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(self.timeout)
            sock.connect(self.address)
        except socket.error as e:
            self._die(e, 'Connection error')

        self.socket = sock

    def _die(self, e, msg='Socket error'):
        """Disconnects from the host and assigns failure retry time. Throws a
        :exc:`~.exceptions.ConnectionError` exception with failure details.
        This is a private method and is meant to be used for any connection
        failures.

        :param e: original exception that caused connection failure.
        :type e: :exc:`socket.error`
        :param msg: optional exception message to indentify operation that was
            being in process (e.g. 'Read error').
        :type msg: string or None
        """
        self.retry_time = time.time() + self.RETRY_INTERVAL
        self.disconnect()

        exmsg = len(e.args) == 1 and e.args[0] or e.args[1]
        raise ConnectionError("%s: %s" % (msg, exmsg))

    def is_ready(self):
        """Checks if connection instance is ready to be used.

        :rtype: bool
        """
        if self.retry_time and self.retry_time > time.time():
            return False
        self.retry_time = 0
        return True

    def disconnect(self):
        """Closes a socket and disassociates it from the connection instance.

        .. note:: It ignores any socket exceptions that might happen in process.
        """
        if self.socket:
            try:
                self.socket.close()
            except socket.error:
                pass
            self.socket = None

    def readline(self):
        """Reads one line from the socket stream and returns it.
        Lines are expected to be delimited with LF.
        Throws :exc:`~.exceptions.ConnectionError` in case of failure.

        :rtype: string

        .. note:: Currently Connection class supports only one line per
           request/response. All data in the stream after first LF will be ignored.
        """
        buffer = ''
        index = -1
        while True:
            index = buffer.find('\n')
            if index >= 0:
                break

            try:
                data = self.socket.recv(4096)
                if self.debug:
                    print("DEBUG: read data bucket: %s" % data)
                if not data:
                    raise RecoverableConnectionError('Connection closed on the remote end.')
            except socket.error as e:
                self._die(e, 'Read error')

            buffer += bytes.decode(data)

        return buffer[:index]

    def send(self, data):
        """Sends all given data into the socket stream.
        Throws :exc:`~.exceptions.ConnectionError` in case of failure.

        :param string data: data to send
        """
        try:
            self.socket.sendall(str.encode(data))
            if self.debug:
                print("DEBUG: sent data: %s" % data)
        except socket.error as e:
            self._die(e, 'Send error')


class HandlerSocket(threading.local):
    """Pool of HandlerSocket connections.

    Manages connections and defines common HandlerSocket operations.
    Uses internal index id cache.
    Subclasses :class:`threading.local` to put connection pool and indexes data
    in thread-local storage as they're not safe to share between threads.

    .. warning::
       Shouldn't be used directly in most cases.
       Use :class:`~.ReadSocket` for read operations and :class:`~.WriteSocket` for
       writes.
    """

    RETRY_LIMIT = 5
    FIND_OPERATIONS = ('=', '>', '>=', '<', '<=')

    def __init__(self, servers, debug=False):
        """Pool constructor initializes connections for all given HandlerSocket servers.

        :param iterable servers: a list of lists that define server data,
            *format*: ``(protocol, host, port, timeout)``.
            See :class:`~.Connection` for details.
        :param bool debug: enable or disable debug mode, default is ``False``.
        """
        self.connections = []
        for server in servers:
            conn = Connection(*server)
            conn.set_debug_mode(debug)
            self.connections.append(conn)

        self._clear_caches()

    def _clear_caches(self):
        """Clears index cache, connection map, index id counter and last cached
        exception.
        Private method.
        """
        self.index_map = {}
        self.current_index_id = 0
        self.index_cache = {}
        self.last_connection_exception = None

    def _get_connection(self, index_id=None, force_index=False):
        """Returns active connection from the pool.

        It will retry available connections in case of connection failure. Max
        retry limit is defined in :const:`~.RETRY_LIMIT`.

        In case of connection failure on all available servers will raise
        :exc:`~.exceptions.ConnectionError`. If ``force_index`` is set, it will
        try only one connection that was used to open given ``index_id``. If that
        fails will throw :exc:`~.exceptions.RecoverableConnectionError`.

        :param index_id: index id to look up connection for, if ``None`` (default)
            or not found a new connection will be returned.
        :type index_id: integer or None
        :param bool force_index: if ``True`` will ensure that only a connection
            that was used to open ``index id`` would be returned, will raise
            :exc:`~.exceptions.OperationalError` otherwise.
        :rtype: :class:`~.Connection` instance
        """
        connections = self.connections[:]
        random.shuffle(connections)
        # Try looking up for index_id in index_map - we should use same connections
        # for opened indexes and operations using them
        if index_id is not None and index_id in self.index_map:
            conn = self.index_map[index_id]
        else:
            if force_index:
                raise OperationalError('There is no connection with given index id "%d"' % index_id)
            conn = connections.pop()

        exception = lambda exc: ConnectionError('Could not connect to any of given servers: %s'\
                                  % exc.args[0])
        # Retry until either limit is reached or all connections tried
        for i in range(max(self.RETRY_LIMIT, len(connections))):
            try:
                if conn.is_ready():
                    conn.connect()
                    break
            except ConnectionError as e:
                self.last_connection_exception = e
                # In case indexed connection is forced remove it from the caches
                # and raise exception so higher level code could retry whole operation
                if force_index:
                    self.purge_index(index_id)
                    if connections:
                        raise RecoverableConnectionError('Could not use connection with given index id "%d"' % index_id)
                    else:
                        # No point retrying if no more connections are available
                        raise exception(self.last_connection_exception)
            if connections:
                conn = connections.pop()
        else:
            raise exception(self.last_connection_exception)

        # If we have an index id, save a relation between it and a connection
        if index_id is not None:
            self.index_map[index_id] = conn
        return conn

    def _parse_response(self, raw_data):
        """Parses HandlerSocket response data.
        Returns a list of result rows which are lists of result columns.
        Raises :exc:`~.exceptions.OperationalError` in case data contains
        a HS error code.
        Private method.

        :param string raw_data: data string returned by HS server.
        :rtype: list
        """
        tokens = raw_data.split('\t')
        if not len(tokens) or int(tokens[0]) != 0:
            error = 'Unknown remote error'
            if len(tokens) > 2:
                error = tokens[2]
            raise OperationalError('HandlerSocket returned an error code: %s' % error)

        columns = int(tokens[1])
        decoded_tokens = map(decode, tokens[2:])
        # Divide response tokens list by number of columns
        data = list(zip(*[decoded_tokens]*columns))

        return data

    def _open_index(self, index_id, db, table, fields, index_name):
        """Calls open index query on HandlerSocket.
        This is a required first operation for any read or write usages.
        Private method.

        :param integer index_id: id number that will be associated with opened index.
        :param string db: database name.
        :param string table: table name.
        :param string fields: comma-separated list of table's fields that would
            be used in further operations. Fields that are part of opened index
            must be present in the same order they are declared in the index.
        :param string index_name: name of the index.
        :rtype: list
        """
        encoded = map(encode, (db, table, index_name, fields))
        query = chain(('P', str(index_id)), encoded)

        response = self._call(index_id, query)

        return response

    def get_index_id(self, db, table, fields, index_name=None):
        """Returns index id for given index data. This id must be used in all
        operations that use given data.

        Uses internal index cache that keys index ids on a combination of:
        ``db:table:index_name:fields``.
        In case no index was found in the cache, a new index will be opened.

        .. note:: ``fields`` is position-dependent, so change of fields order will open
           a new index with another index id.

        :param string db: database name.
        :param string table: table name.
        :param iterable fields: list of table's fields that would be used in further
            operations. See :meth:`._open_index` for more info on fields order.
        :param index_name: name of the index, default is ``PRIMARY``.
        :type index_name: string or None
        :rtype: integer or None
        """
        index_name = index_name or 'PRIMARY'
        fields = ','.join(fields)
        cache_key = ':'.join((db, table, index_name, fields))
        index_id = self.index_cache.get(cache_key)
        if index_id is not None:
            return index_id

        response = self._open_index(self.current_index_id, db, table, fields, index_name)
        if response is not None:
            index_id = self.current_index_id
            self.index_cache[cache_key] = index_id
            self.current_index_id += 1
            return index_id

        return None

    def purge_indexes(self):
        """Closes all indexed connections, cleans caches, zeroes index id counter.
        """
        for conn in self.index_map.values():
            conn.disconnect()

        self._clear_caches()

    def purge(self):
        """Closes all connections, cleans caches, zeroes index id counter."""
        for conn in self.connections:
            conn.disconnect()

        self._clear_caches()

    def purge_index(self, index_id):
        """Clear single index connection and cache.

        :param integer index_id: id of the index to purge.
        """
        del self.index_map[index_id]
        for key, value in self.index_cache.items():
            if value == index_id:
                del self.index_cache[key]

    def _call(self, index_id, query, force_index=False):
        """Helper that performs actual data exchange with HandlerSocket server.
        Returns parsed response data.

        :param integer index_id: id of the index to operate on.
        :param iterable query: list/iterable of tokens ready for sending.
        :param bool force_index: pass ``True`` when operation requires connection
            with given ``index_id`` to work. This is usually everything except
            index opening. See :meth:`~._get_connection`.
        :rtype: list
        """
        conn = self._get_connection(index_id, force_index)
        try:
            conn.send('\t'.join(query)+'\n')
            response = self._parse_response(conn.readline())
        except ConnectionError as e:
            self.purge_index(index_id)
            raise e

        return response


class ReadSocket(HandlerSocket):
    """HandlerSocket client for read operations."""

    def find(self, index_id, operation, columns, limit=0, offset=0):
        """Finds row(s) via opened index.

        Raises ``ValueError`` if given data doesn't validate.

        :param integer index_id: id of opened index.
        :param string operation: logical comparison operation to use over ``columns``.
            Currently allowed operations are defined in :const:`~.FIND_OPERATIONS`.
            Only one operation is allowed per call.
        :param iterable columns: list of column values for comparison operation.
            List must be ordered in the same way as columns are defined
            in opened index.
        :param integer limit: optional limit of results to return. Default is
            one row. In case multiple results are expected, ``limit`` must be
            set explicitly, HS wont return all found rows by default.
        :param integer offset: optional offset of rows to search for.
        :rtype: list
        """
        if operation not in self.FIND_OPERATIONS:
            raise ValueError('Operation is not supported.')

        if not check_columns(columns):
            raise ValueError('Columns must be a non-empty iterable.')

        query = chain(
            (str(index_id), operation, str(len(columns))),
            map(encode, columns),
            (str(limit), str(offset))
        )

        response = self._call(index_id, query, force_index=True)

        return response


class WriteSocket(HandlerSocket):
    """HandlerSocket client for write operations."""

    MODIFY_OPERATIONS = ('U', 'D', '+', '-', 'U?', 'D?', '+?', '-?')

    def find_modify(self, index_id, operation, columns, modify_operation,
                    modify_columns=[], limit=0, offset=0):
        """Updates/deletes row(s) using opened index.

        Returns number of modified rows or a list of original values in case
        ``modify_operation`` ends with ``?``.

        Raises ``ValueError`` if given data doesn't validate.

        :param integer index_id: id of opened index.
        :param string operation: logical comparison operation to use over ``columns``.
            Currently allowed operations are defined in :const:`~.FIND_OPERATIONS`.
            Only one operation is allowed per call.
        :param iterable columns: list of column values for comparison operation.
            List must be ordered in the same way as columns are defined in
            opened index.
        :param string modify_operation: modification operation (update or delete).
            Currently allowed operations are defined in :const:`~.MODIFY_OPERATIONS`.
        :param iterable modify_columns: list of column values for update operation.
            List must be ordered in the same way as columns are defined in
            opened index. Only usable for *update* operation,
        :param integer limit: optional limit of results to change. Default is
            one row. In case multiple rows are expected to be changed, ``limit``
            must be set explicitly, HS wont change all found rows by default.
        :param integer offset: optional offset of rows to search for.
        :rtype: list

        """
        if operation not in self.FIND_OPERATIONS \
                or modify_operation not in self.MODIFY_OPERATIONS:
            raise ValueError('Operation is not supported.')

        if not check_columns(columns):
            raise ValueError('Columns must be a non-empty iterable.')

        if modify_operation in ('U', '+', '-', 'U?', '+?', '-?') \
            and not check_columns(modify_columns):
            raise ValueError('Modify_columns must be a non-empty iterable for update operation')

        query = chain(
            (str(index_id), operation, str(len(columns))),
            map(encode, columns),
            (str(limit), str(offset), modify_operation),
            map(encode, modify_columns)
        )

        response = self._call(index_id, query, force_index=True)

        return response

    def insert(self, index_id, columns):
        """Inserts single row using opened index.

        Raises ``ValueError`` if given data doesn't validate.

        :param integer index_id: id of opened index.
        :param list columns: list of column values for insertion. List must be
            ordered in the same way as columns are defined in opened index.
        :rtype: bool
        """
        if not check_columns(columns):
            raise ValueError('Columns must be a non-empty iterable.')

        query = chain(
            (str(index_id), '+', str(len(columns))),
            map(encode, columns)
        )

        self._call(index_id, query, force_index=True)

        return True
