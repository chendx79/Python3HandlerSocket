:mod:`manager`
==============
.. automodule:: pyhs.manager

    .. autoclass:: Manager
        :members: get, purge

        .. automethod:: find(db, table, operation, fields, values, index_name=None, limit=0, offset=0)
        .. automethod:: insert(db, table, fields, index_name=None)
        .. automethod:: update(db, table, operation, fields, values, update_values, index_name=None, limit=0, offset=0, return_original=False)
        .. automethod:: incr(db, table, operation, fields, values, step=['1'], index_name=None, limit=0, offset=0, return_original=False)
        .. automethod:: decr(db, table, operation, fields, values, step=['1'], index_name=None, limit=0, offset=0, return_original=False)
        .. automethod:: delete(db, table, operation, fields, values, index_name=None, limit=0, offset=0, return_original=False)
