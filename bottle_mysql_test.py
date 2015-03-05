import unittest

import bottle
import bottle_mysql

from _mysql_exceptions import OperationalError

'''
TODO

add more test cases

'''

class BottleMySQLTest(unittest.TestCase):
    USER = 'root'
    PASS = ''
    DBNAME = 'bottle_mysql_test'
    SOCKET = '/var/run/mysqld/mysqld.sock'

    def test_echo(self):
        def test(db):
            db.execute(''' SELECT 1 AS TEST ''')

            self.assertEqual({'TEST': 1}, db.fetchone())

        '''test normal'''
        self._run(self._app(), test)

        '''test socket'''
        self._run(self._app(dbunixsocket=self.SOCKET), test)

    def test_badsocket(self):

        sock = '/not_exits.sock'
        try:
            def empty(db):
                pass

            self._run(self._app(dbunixsocket=sock, ), empty)
        except OperationalError as e:
            self.assertTrue(sock in e.args[1])
            return

        self.fail('should not success')

    def test_badhost(self):

        host = '255.255.255.255'
        try:
            def empty(db):
                pass

            self._run(self._app(dbhost=host, ), empty)
        except OperationalError as e:
            self.assertTrue(host in e.args[1])
            return

        self.fail('should not success')

    def _run(self, app, f):
        app.get('/')(f)
        self._request(app, '/')

    def _app(self, **kwargs):
        app = bottle.Bottle(catchall=False)

        kwargs.setdefault('dbuser', self.USER)
        kwargs.setdefault('dbpass', self.PASS)
        kwargs.setdefault('dbname', self.DBNAME)
        plugin = bottle_mysql.Plugin(**kwargs)

        app.install(plugin)

        return app

    def _request(self, app, path, method='GET'):
        return app({'PATH_INFO': path, 'REQUEST_METHOD': method}, lambda x, y: None)


if __name__ == '__main__':
    unittest.main()
