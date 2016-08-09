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
__version__ = '0.3.1'
__license__ = 'MIT'

### CUT HERE (see setup.py)

import inspect
import MySQLdb
import MySQLdb.cursors as cursors
import bottle


# PluginError is defined to bottle >= 0.10
if not hasattr(bottle, 'PluginError'):
    class PluginError(bottle.BottleException):
        pass

    bottle.PluginError = PluginError


class MySQLPlugin(object):
    '''
    This plugin passes a mysql database handle to route callbacks
    that accept a `db` keyword argument. If a callback does not expect
    such a parameter, no connection is made. You can override the database
    settings on a per-route basis.
    '''

    name = 'mysql'
    api = 2

    def __init__(self, dbuser=None, dbpass=None, dbname=None, dbhost='localhost', dbport=3306, dbunixsocket=None,
                 autocommit=True, dictrows=True, keyword='db', charset='utf8', timezone=None, conv=None):
        self.dbhost = dbhost
        self.dbport = dbport
        self.dbunixsocket = dbunixsocket
        self.dbuser = dbuser
        self.dbpass = dbpass
        self.dbname = dbname
        self.autocommit = autocommit
        self.dictrows = dictrows
        self.keyword = keyword
        self.charset = charset
        self.timezone = timezone
        self.conv = conv

    def setup(self, app):
        '''
        Make sure that other installed plugins don't affect the same keyword argument.
        '''
        for other in app.plugins:
            if not isinstance(other, MySQLPlugin):
                continue
            if other.keyword == self.keyword:
                raise PluginError("Found another mysql plugin with conflicting settings (non-unique keyword).")
            elif other.name == self.name:
                self.name += '_%s' % self.keyword

    def apply(self, callback, route):
        # hack to support bottle v0.9.x
        if bottle.__version__.startswith('0.9'):
            config = route['config']
            _callback = route['callback']
        else:
            config = route.config
            _callback = route.callback

        # Override global configuration with route-specific values.
        if "mysql" in config:
            # support for configuration before `ConfigDict` namespaces
            g = lambda key, default: config.get('mysql', {}).get(key, default)
        else:
            g = lambda key, default: config.get('mysql.' + key, default)

        dbhost = g('dbhost', self.dbhost)
        dbport = g('dbport', self.dbport)
        dbunixsocket = g('dbunixsocket', self.dbunixsocket)
        dbuser = g('dbuser', self.dbuser)
        dbpass = g('dbpass', self.dbpass)
        dbname = g('dbname', self.dbname)
        autocommit = g('autocommit', self.autocommit)
        dictrows = g('dictrows', self.dictrows)
        keyword = g('keyword', self.keyword)
        charset = g('charset', self.charset)
        timezone = g('timezone', self.timezone)
        conv = g('conv', self.conv)

        # Test if the original callback accepts a 'db' keyword.
        # Ignore it if it does not need a database handle.
        _args = inspect.getargspec(_callback)
        if keyword not in _args.args:
            return callback

        def wrapper(*args, **kwargs):
            # Connect to the database
            con = None
            try:

                kw = {
                    'user': dbuser,
                    'passwd': dbpass,
                    'db': dbname,
                    'charset': charset,
                }

                if dictrows:
                    kw['cursorclass'] = cursors.DictCursor

                if conv:
                    kw['conv'] = conv

                if dbunixsocket:
                    kw['unix_socket'] = dbunixsocket
                else:
                    kw['host'] = dbhost
                    kw['port'] = dbport

                con = MySQLdb.connect(**kw)

                cur = con.cursor()
                if timezone:
                    cur.execute("set time_zone=%s", (timezone, ))

            except bottle.HTTPResponse as e:
                raise bottle.HTTPError(500, "Database Error", e)

            # Add the connection handle as a keyword argument.
            kwargs[keyword] = cur

            try:
                rv = callback(*args, **kwargs)
                if autocommit:
                    con.commit()
            except MySQLdb.IntegrityError as e:
                con.rollback()
                raise bottle.HTTPError(500, "Database Error", e)
            except bottle.HTTPError:
                raise
            except bottle.HTTPResponse:
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
