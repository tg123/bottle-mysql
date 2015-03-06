import unittest

import bottle
import bottle_mysql
import MySQLdb

from _mysql_exceptions import OperationalError


class BottleMySQLTest(unittest.TestCase):
    USER = 'root'
    PASS = ''
    DBNAME = 'bottle_mysql_test'
    SOCKET = '/var/run/mysqld/mysqld.sock'
    DBHOST = '127.0.0.1'

    # copy from https://github.com/bottlepy/bottle-sqlite
    def test_with_keyword(self):
        def test(db):
            self.assertTrue(isinstance(db, MySQLdb.cursors.BaseCursor))

        self._run(test)

    def test_without_keyword(self):
        def test_1():
            pass

        self._run(test_1)

        def test_2(**kw):
            self.assertFalse('db' in kw)

        self._run(test_2)

    def test_install_conflicts(self):

        app = self._app()  # install default
        app = self._app(app=app, keyword='db2')  # install another

        def test(db, db2):
            self.assertEqual(type(db), type(db2))

        self._run(test, app)

    def test_echo(self):
        def test(db):
            db.execute(''' SELECT 1 AS TEST ''')

            self.assertEqual({'TEST': 1}, db.fetchone())

        # test normal
        self._run(test, self._app(dbhost=self.DBHOST))

        # test socket
        self._run(test, self._app(dbunixsocket=self.SOCKET))

    def test_bad_connection(self):

        def should_raise(app, word):
            try:
                def empty(db):
                    pass

                self._run(empty, app)
            except OperationalError as e:
                self.assertTrue(word in e.args[1])
                return

            self.fail('should not success')


        # bad sock
        sock = '/not_exits.sock'
        should_raise(self._app(dbunixsocket=sock), sock)

        # bad host
        host = '255.255.255.255'
        should_raise(self._app(dbhost=host), host)

    def test_dictrow(self):

        def equal_type(t):
            def test_type(db):
                db.execute(''' SELECT 1 AS TEST ''')
                self.assertEqual(type(db.fetchone()), t)

            return test_type

        # default
        self._run(equal_type(dict), app=self._app())

        # disable dictrows
        self._run(equal_type(tuple), app=self._app(dictrows=False))

    def test_timezone(self):

        def equal_tz(tz):
            def query_timezone(db):
                db.execute(''' SELECT @@session.time_zone as TZ;''')
                self.assertEqual({'TZ': tz}, db.fetchone())

            return query_timezone

        tz = '-08:00'
        self._run(equal_tz(tz), app=self._app(timezone=tz))

        # default tz
        self._run(equal_tz('SYSTEM'))

    def test_crud(self):

        self._create_test_table()

        def crud(db):
            data = 'test'

            # insert
            rows = db.execute(''' INSERT INTO `bottle_mysql_test` VALUE (NULL, %s) ''', (data,))
            self.assertGreater(rows, 0)

            db.execute(''' SELECT last_insert_id() as ID ''')

            data_id = db.fetchone()['ID']
            self.assertGreater(data_id, 0)

            # select
            db.execute(''' SELECT * FROM `bottle_mysql_test` WHERE `id` = %s''', (data_id, ))
            self.assertEqual({'id': data_id, 'text': data, }, db.fetchone())

            # update
            data = 'new'
            rows = db.execute(''' UPDATE `bottle_mysql_test` SET `text` = %s WHERE `id` = %s''', (data, data_id, ))
            self.assertGreater(rows, 0)

            db.execute(''' SELECT * FROM `bottle_mysql_test` WHERE `id` = %s''', (data_id, ))
            self.assertEqual({'id': data_id, 'text': data, }, db.fetchone())

            # delete
            rows = db.execute(''' DELETE FROM `bottle_mysql_test` WHERE `id` = %s''', (data_id, ))
            self.assertGreater(rows, 0)

        self._run(crud)

    def test_autocommit(self):
        self._create_test_table()

        self._run(self._insert_one)

        self.assert_records(1)

    def test_not_autocommit(self):
        self._create_test_table()

        app = self._app()

        # config with override
        @app.get('/', mysql={'autocommit': False})
        def insert(db):
            self._insert_one(db)

        self._request(app, '/')
        self.assert_records(0)

        # config with construct
        self._run(self._insert_one, self._app(autocommit=False))
        self.assert_records(0)

    def test_commit_on_redirect(self):
        self._create_test_table()

        def test(db):
            self._insert_one(db)
            bottle.redirect('/')

        self._run(test)
        self.assert_records(1)

    def test_commit_on_abort(self):
        self._create_test_table()

        def test(db):
            self._insert_one(db)
            bottle.abort()

        self._run(test)
        self.assert_records(0)

    def assert_records(self, count):
        def query_count(db):
            db.execute('''SELECT COUNT(1) AS c FROM `bottle_mysql_test`''')
            self.assertEqual({'c': count}, db.fetchone())

        self._run(query_count)

    def _insert_one(self, db, data='test'):
        rows = db.execute(''' INSERT INTO `bottle_mysql_test` VALUE (NULL, %s) ''', (data,))
        self.assertEqual(rows, 1)

    def _create_test_table(self):
        def init(db):
            db.execute('''DROP TABLE IF EXISTS `bottle_mysql_test`; ''')

            db.execute('''
            CREATE TABLE `bottle_mysql_test` (
              `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
              `text` varchar(11) DEFAULT NULL,
              PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
            ''')

        self._run(init)

    def _run(self, f, app=None):

        if not app:
            app = self._app()

        app.get('/')(f)
        self._request(app, '/')

    def _app(self, **kwargs):
        app = kwargs.pop('app', bottle.Bottle(catchall=False))

        kwargs.setdefault('dbuser', self.USER)
        kwargs.setdefault('dbpass', self.PASS)
        kwargs.setdefault('dbname', self.DBNAME)
        kwargs.setdefault('dbhost', self.DBHOST)
        plugin = bottle_mysql.Plugin(**kwargs)

        app.install(plugin)

        return app

    def _request(self, app, path, method='GET'):
        return app({'PATH_INFO': path, 'REQUEST_METHOD': method}, lambda x, y: None)


if __name__ == '__main__':
    unittest.main()
