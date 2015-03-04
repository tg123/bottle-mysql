Bottle-MySQL
============

MySQL is the world's most used relational database management system (RDBMS) that runs
as a server providing multi-user access to a number of databases.

This plugin simplifies the use of mysql databases in your Bottle applications. 
Once installed, all you have to do is to add an ``db`` keyword argument 
(configurable) to route callbacks that need a database connection.


`Bottle-MySQL` is written by Michael Lustfield [MTecknology](https://github.com/MTecknology)
and now is maintained by Boshi Lian (tgic).


Installation
------------

Install using pip:

    $ pip install bottle-mysql

or download the latest version from github:

    $ git clone git://github.com/tg123/bottle-mysql.git
    $ cd bottle-mysql
    $ python setup.py install

Usage
-----

Once installed to an application, the plugin passes an open 
:class:`MySQLdb.connect().cursor()` instance to all routes that requires an ``db`` keyword 
argument:

    import bottle
    import bottle_mysql

    app = bottle.Bottle()
    # dbhost is optional, default is localhost
    plugin = bottle_mysql.Plugin(dbuser='user', dbpass='pass', dbname='some_db')
    app.install(plugin)

    @app.route('/show/<item>')
    def show(item, db):
        db.execute('SELECT * from items where name="%s"', (item,))
        row = db.fetchone()
        if row:
            return template('showitem', page=row)
        return HTTPError(404, "Page not found")

Routes that do not expect an ``db`` keyword argument are not affected.

The connection handle is configurable so that rows can be returned as either an
index (like tuples) or as dictionaries. At the end of the request cycle, outstanding
transactions are committed and the connection is closed automatically. If an error
occurs, any changes to the database since the last commit are rolled back to keep
the database in a consistent state.

Configuration
-------------

The following configuration options exist for the plugin class:

* **dbuser**: Username that will be used to connect to the database (default: None).
* **dbpass**: Password that will be used to connect to the database (default: None).
* **dbname**: Database name that will be connected to (default: None).
* **dbhost**: Databse server host (default: 'localhost').
* **dbport**: Databse server port (default: 3306).
* **dbunixsocket**: Optionally, you can use a unix socket rather than TCP/IP.
* **keyword**: The keyword argument name that triggers the plugin (default: 'db').
* **autocommit**: Whether or not to commit outstanding transactions at the end of the request cycle (default: True).
* **dictrows**: Whether or not to support dict-like access to row objects (default: True).
* **charset**: Database connection charset (default: 'utf8')
* **timezone**: Database connection time zone (default: None).

You can override each of these values on a per-route basis: 

    @app.route('/cache/<item>', mysql={'dbname': 'xyz_db'})
    def cache(item, db):
        ...
   
or install two plugins with different ``keyword`` settings to the same application:

    app = bottle.Bottle()
    local_db = bottle_mysql.Plugin(dbuser='user', dbpass='pass', dbname='local_db')
    prod_db = bottle_mysql.Plugin(dbuser='user', dbpass='pass', dbname='some_db', dbhost='sql.domain.tld', keyword='remote_db')
    app.install(local_db)
    app.install(prod_db)

    @app.route('/show/<item>')
    def show(item, db):
        ...

    @app.route('/cache/<item>')
    def cache(item, remote_db):
        ...
