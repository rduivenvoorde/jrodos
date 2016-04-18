import psycopg2
import psycopg2.extras
import credentials
import urllib2


class Database():
    def __init__(self, conn_code):
        self.conn_string = self.get_conn_string(conn_code)
        self.db_ok = False
        self.error = ''

    def __str__(self):
        return 'Database[' + self.conn_string + ']'

    def connect(self):
        try:
            self.connection = psycopg2.connect(self.conn_string)
            self.db_ok = True
        except psycopg2.Error as e:
            self.db_ok = False
            self.error = e
            #return self.connection

    def disconnect(self):
        self.connection.close()

    def get_conn_string(self, code):
        if code == 'jrodos':
            return credentials.conn_string_rodoshome
        if code == 'sectorplot':
            return credentials.conn_string_sectorplot

    def execute(self, queries):
        self.connect()
        if not self.db_ok:
            return {'db_ok':self.db_ok , 'error': self.error}
        cursor = self.connection.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
        for query in queries:
            cursor.execute(query['text'], query['vals'])
        #print(cursor.statusmessage)
        #print(cursor.rowcount)
        if 'SELECT' in str(cursor.statusmessage):
            memory = cursor.fetchall()
        else:
            memory = None
        self.connection.commit()
        cursor.close()
        self.disconnect()
        if memory is None:
            return {'db_ok': self.db_ok}
        else:
            return {'db_ok': self.db_ok, 'data': memory}


class RestClient():
    def __init__(self, conn_code):
        gs_conn = self.get_conn(conn_code)
        self.user = gs_conn['user']
        self.password = gs_conn['password']
        self.top_level_url = gs_conn['top_level_url']

        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, self.top_level_url, self.user, self.password)
        handler = urllib2.HTTPBasicAuthHandler(password_mgr)
        self.opener = urllib2.build_opener(handler)

    def __str__(self):
        return 'RestClient[' + self.top_level_url + ']'

    def get_conn(self, code):
        if code == 'sectorplot':
            return credentials.gs_conn_sectorplot

    def doRequest(self, url, data=None, headers=None, method='POST'):
        #print 'url:    ', url
        #print 'data:   ', data
        #print 'headers:', headers
        req = urllib2.Request(url=url, data=data, headers=headers)
        req.get_method = lambda: method
        f = self.opener.open(req)
        #print f.read()
        return f.read()






if __name__ == "__main__":
    db = Database('sectorplot')
    #db = Database('jrodos')

    q = {}
    q['text'] = 'SELECT 0 as "col1"'
    q['vals'] = ()

    r = db.execute([q])
    if r['db_ok']:
        print r['data'][0].col1
    else:
        print r['error']

