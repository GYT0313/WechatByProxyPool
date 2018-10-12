import pymysql
from Weixin.config import *

class MySQL():
    def __init__(self, host=MYSQL_HOST, username=MYSQL_USER, password=MYSQL_PASSWORD, port=MYSQL_PORT, database=MYSQL_DATABASE):
        """[summary]
        
        mysql初始化
        
        Keyword Arguments:
            host {[type]} -- [description] (default: {MYSQL_HOST})
            username {[type]} -- [description] (default: {MYSQL_USER})
            password {[type]} -- [description] (default: {MYSQL_PASSWORD})
            port {[type]} -- [description] (default: {MYSQL_PORT})
            database {[type]} -- [description] (default: {MYSQL_DATABASE})
        """
        try:
            self.db = pymysql.connect(host, username, password, database, charset='utf8', port=port)
            self.cursor = self.db.cursor()
        except pymysql.MySQLError as e:
            print(e.args)

    def insert(self, table, data):
        """[summary]
        
        插入数据
        
        Arguments:
            table {[type]} -- [description]
            data {[type]} -- [description]
        """
        keys = ', '.join(data.keys)
        #  '%s, %s, %s, %s, %s'
        values = ', '.join(['%s'] * len(data))
        # 构造sql 语句
        sql_query = 'insert into %s (%s) values (%s) ' % (table, keys, values)
        try:
            self.cursor.execute(sql_query, tuple(data.values()))
            self.db.commit()
        except pymysql.MySQLError as e:
            print(e.args)
            # 插入失败，回滚
            self.db.rollback()

