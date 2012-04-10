'''
Bottle-MySQL is a plugin that integrates MySQL with your Bottle
application. It automatically connects to a database at the beginning of a
request, passes the database handle to the route callback and closes the
connection afterwards.

To automatically detect routes that need a database connection, the plugin
searches for route callbacks that require a `db` keyword argument
(configurable) and skips routes that do not. This removes any overhead for
routes that don't need a database connection.

Results are returned as dictionaries.

Usage Example::

    import bottle
    import bottle_mysql

    app = bottle.Bottle()
    # dbhost is optional, default is localhost
    plugin = bottle_mysql.Plugin(dbuser='user', dbpass='pass', dbname='db')
    app.install(plugin)

    @app.route('/show/:<tem>')
    def show(item, db):
        db.execute('SELECT * from items where name="%s"', (item,))
        row = db.fetchone()
        if row:
            return template('showitem', page=row)
        return HTTPError(404, "Page not found")
'''

__author__ = "Michael Lustfield"
__version__ = '0.1.1'
__license__ = 'MIT'

### CUT HERE (see setup.py)

import inspect
import MySQLdb
import MySQLdb.cursors as cursors
from bottle import HTTPResponse, HTTPError


class MySQLPlugin(object):
    '''
    This plugin passes a mysql database handle to route callbacks
    that accept a `db` keyword argument. If a callback does not expect
    such a parameter, no connection is made. You can override the database
    settings on a per-route basis.
    '''

    name = 'mysql'

    def __init__(self, dbuser=None, dbpass=None, dbname=None, dbhost='localhost', autocommit=True, dictrows=True, keyword='db'):
         self.dbhost = dbhost
         self.dbuser = dbuser
         self.dbpass = dbpass
         self.dbname = dbname
         self.autocommit = autocommit
         self.dictrows = dictrows
         self.keyword = keyword

    def setup(self, app):
        '''
        Make sure that other installed plugins don't affect the same keyword argument.
        '''
        for other in app.plugins:
            if not isinstance(other, MySQLPlugin):
                continue
            if other.keyword == self.keyword:
                raise PluginError("Found another mysql plugin with conflicting settings (non-unique keyword).")

    def apply(self, callback, context):
        # Override global configuration with route-specific values.
        conf = context['config'].get('mysql') or {}
        dbhost = conf.get('dbhost', self.dbhost)
        dbuser = conf.get('dbuser', self.dbuser)
        dbpass = conf.get('dbpass', self.dbpass)
        dbname = conf.get('dbname', self.dbname)
        autocommit = conf.get('autocommit', self.autocommit)
        dictrows = conf.get('dictrows', self.dictrows)
        keyword = conf.get('keyword', self.keyword)

        # Test if the original callback accepts a 'db' keyword.
        # Ignore it if it does not need a database handle.
        args = inspect.getargspec(context['callback'])[0]
        if keyword not in args:
            return callback

        def wrapper(*args, **kwargs):
            # Connect to the database
            con = None
            try:
                # Using DictCursor lets us return result as a dictionary instead of the default list
                if dictrows:
                    con = MySQLdb.connect(dbhost, dbuser, dbpass, dbname, cursorclass=cursors.DictCursor);
                else:
                    con = MySQLdb.connect(dbhost, dbuser, dbpass, dbname);
                cur = con.cursor()
            except HTTPResponse, e:
                raise HTTPError(500, "Database Error", e)

            # Add the connection handle as a keyword argument.
            kwargs[keyword] = cur

            try:
                rv = callback(*args, **kwargs)
                if autocommit:
                    con.commit()
            except MySQLdb.IntegrityError, e:
                con.rollback()
                raise HTTPError(500, "Database Error", e)
            except HTTPError, e:
                raise
            except HTTPResponse, e:
                if autocommit:
                    con.commit()
                raise
            finally:
                if con:
                    con.close()
            return rv

        # Replace the route callback with the wrapped one.
        return wrapper

Plugin = MySQLPlugin
