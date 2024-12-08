import abc
import os
import time
from general.executer import EXECUTER
from general.logger import LOG

SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "source", "sql")
TABLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "source", "table")
JS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "source", "mongo_js")


class node_base(abc.ABC):
    '''
    节点的基类
    对于该类处理，其输入输出均需要在数据库中备份
    所以这类节点的输入输出都应当是数据库和文件这类io,不提供变量模式的传递
    '''

    def __init__(self, node_define: dict) -> None:
        self.name = node_define["name"]
        self.next_name = node_define["next_name"]
        self.type = node_define["type"]
        if 


    def run(self) -> tuple[str, int]:
        self.LOG.info("开始计算")
        data_size = 0
        try:
            t = time.perf_counter()
            connect_ = self.connect()
            data_ = self.read(connect_["source_sql"], connect_["source_connect"])
            self.write(data_["data"], connect_["target_connect"])
            t = time.perf_counter() - t
            self.LOG.info("计算耗时为" + str(t) + "s")
            data_size = data_["data_size"]
        except:
            self.LOG.error(traceback.format_exc())
        self.LOG.info("计算结束")
        return self.name, data_size

    @abc.abstractmethod
    def read(self):
        ...

    @abc.abstractmethod
    def write(self):
        ...


def get_data_size(data) -> int:
    '''获取内存占用,用于计算同步时间间隔'''
    return int(getsizeof(data) / 1024 **2)

class sql_to_table(node_base):
    allow_type = ["sql_to_table"]

    def __init__(self, node_define: dict) -> None:
        super().__init__(node_define["name"], node_define["next_name"], db_engine, node_define["type"])
        self.source: dict = node_define["source"]
        self.target: dict = node_define["target"]
        self.data: pd.DataFrame | None = None
        # 检查节点格式是否符合要求
        source_key = self.source.keys()
        assert "connect" in source_key, "节点的格式不符合要求：source中没有connect"
        assert "sql" in source_key, "节点的格式不符合要求：source中没有sql"
        target_key = self.target.keys()
        assert "connect" in target_key, "节点的格式不符合要求：target中没有connect"
        assert "table" in target_key, "节点的格式不符合要求：target中没有table"

    def connect(self) -> dict:
        self.LOG.info("开始连接")
        source_connect = self.temp_db.get_sql(self.source["connect"])
        target_connect = self.temp_db.get_sql(self.target["connect"])
        source_sql = ""
        with open(os.path.join(SQL_PATH, self.source["sql"]), 'r', encoding='utf8') as file:
            # 确保输入没有参数匹配全是字符串
            source_sql = text(file.read())
        return {
            "source_connect":source_connect, 
            "target_connect":target_connect, 
            "source_sql":source_sql
        }

    def read(self, source_sql: str, source_connect: sqlalchemy.Connection) -> dict:
        try:
            self.LOG.info("正在执行sql:" + str(os.path.join(SQL_PATH, self.source["sql"])))
            data = pd.read_sql_query(source_sql, source_connect)
            self.LOG.info("数据形状为: " + str(data.shape[0]) + "," + str(data.shape[1]))
            return {
                "data":data, 
                "data_size":data.shape[0] * data.shape[1]
            }
        except:
            self.LOG.error(traceback.format_exc())
            self.LOG.info("正在回滚")
            source_connect.rollback()
        finally:
            source_connect.close()
        return {
                "data": None, 
                "data_size": 0
            }
        
    def write(self, data: pd.DataFrame, target_connect: sqlalchemy.Connection) -> None:
        try:
            self.LOG.info("正在写入表:" + self.target["table"])
            schema = self.target["schema"] if "schema" in self.target.keys() else None
            data.to_sql(name=self.target["table"], con=target_connect, schema=schema, index=False, if_exists='replace', chunksize=1000)
        except:
            self.LOG.error(traceback.format_exc())
            self.LOG.info("正在回滚")
            target_connect.rollback()
        finally:
            target_connect.close()



class table_to_table(node_base):
    allow_type = ["table_to_table"]

    def __init__(self, node_define: dict) -> None:
        super().__init__(node_define["name"], node_define["next_name"], db_engine, node_define["type"])
        self.source: dict = node_define["source"]
        self.target: dict = node_define["target"]
        self.data: pd.DataFrame | None = None
        # 检查节点格式是否符合要求
        source_key = self.source.keys()
        assert "connect" in source_key, "节点的格式不符合要求：source中没有connect"
        assert "table" in source_key, "节点的格式不符合要求：source中没有table"
        target_key = self.target.keys()
        assert "connect" in target_key, "节点的格式不符合要求：target中没有connect"
        assert "table" in target_key, "节点的格式不符合要求：target中没有table"

    def connect(self) -> dict:
        self.LOG.info("开始连接")
        source_connect = self.temp_db.get_sql(self.source["connect"])
        target_connect = self.temp_db.get_sql(self.target["connect"])
        if "schema" in self.source.keys():
            source_sql = text("select * from " + self.source["schema"] + "." + self.source["table"])
        else:
            source_sql = text("select * from " + self.source["table"])
        return {
            "source_connect":source_connect, 
            "target_connect":target_connect, 
            "source_sql":source_sql
        }

    def read(self, source_sql: str, source_connect: sqlalchemy.Connection) -> dict:
        try:
            self.LOG.info("正在执行sql:" + str(source_sql))
            data = pd.read_sql_query(source_sql, source_connect)
            self.LOG.info("数据形状为: " + str(data.shape[0]) + "," + str(data.shape[1]))
            return {
                "data":data, 
                "data_size":data.shape[0] * data.shape[1]
            }
        except:
            self.LOG.error(traceback.format_exc())
            self.LOG.info("正在回滚")
            source_connect.rollback()
        finally:
            source_connect.close()
        return {
                "data": None, 
                "data_size": 0
            }

    def write(self, data: pd.DataFrame, target_connect: sqlalchemy.Connection) -> None:
        try:
            self.LOG.info("正在写入表:" + self.target["table"])
            schema = self.target["schema"] if "schema" in self.target.keys() else None
            data.to_sql(name=self.target["table"], con=target_connect, schema=schema, index=False, if_exists='replace', chunksize=1000)
        except:
            self.LOG.error(traceback.format_exc())
            self.LOG.info("正在回滚")
            target_connect.rollback()
        finally:
            target_connect.close()


class sql_to_nosql(node_base):
    allow_type = ["sql_to_nosql"]

    def __init__(self, node_define: dict) -> None:
        super().__init__(node_define["name"], node_define["next_name"], db_engine, node_define["type"])
        self.source: dict = node_define["source"]
        self.target: dict = node_define["target"]
        self.data: pd.DataFrame | None = None
        # 检查节点格式是否符合要求
        source_key = self.source.keys()
        assert "connect" in source_key, "节点的格式不符合要求：source中没有connect"
        assert "sql" in source_key, "节点的格式不符合要求：source中没有sql"
        target_key = self.target.keys()
        assert "connect" in target_key, "节点的格式不符合要求：target中没有connect"
        assert "database" in target_key, "节点的格式不符合要求：target中没有database"
        assert "table" in target_key, "节点的格式不符合要求：target中没有table"

    def connect(self) -> dict:
        self.LOG.info("开始连接")
        source_connect = self.temp_db.get_sql(self.source["connect"])
        target_connect = self.temp_db.get_nosql(self.target["connect"])[self.target["database"]]
        with open(os.path.join(SQL_PATH, self.source["sql"]), 'r', encoding='utf8') as file:
            # 确保输入没有参数匹配全是字符串
            source_sql = text(file.read())
        return {
            "source_connect":source_connect, 
            "target_connect":target_connect, 
            "source_sql":source_sql
        }

    def read(self, source_sql: str, source_connect: sqlalchemy.Connection) -> dict:
        try:
            self.LOG.info("正在执行sql:" + str(os.path.join(SQL_PATH, self.source["sql"])))
            data = pd.read_sql_query(source_sql, source_connect)
            for col_name in data.columns:
                data[[col_name]] = data[[col_name]].astype(object).where(data[[col_name]].notnull(), None)
            self.LOG.info("数据形状为: " + str(data.shape[0]) + "," + str(data.shape[1]))
            return {
                "data":data, 
                "data_size":data.shape[0] * data.shape[1]
            }
        except:
            self.LOG.error(traceback.format_exc())
            self.LOG.info("正在回滚")
            source_connect.rollback()
        finally:
            source_connect.close()
        return {
                "data": None, 
                "data_size": 0
            }

    def write(self, data: pd.DataFrame, target_connect: pymongo.database.Database) -> None:
        try:
            self.LOG.info("正在清空表:" + self.target["table"])
            target_connect[self.target["table"]].drop()
            self.LOG.info("正在写入表:" + self.target["table"])
            data = data.to_dict('records')
            target_connect[self.target["table"]].insert_many(data)
        except:
            self.LOG.error(traceback.format_exc())


class table_to_nosql(node_base):
    allow_type = ["table_to_nosql"]

    def __init__(self, node_define: dict) -> None:
        super().__init__(node_define["name"], node_define["next_name"], db_engine, node_define["type"])
        self.source: dict = node_define["source"]
        self.target: dict = node_define["target"]
        self.data: pd.DataFrame | None = None
        # 检查节点格式是否符合要求
        source_key = self.source.keys()
        assert "connect" in source_key, "节点的格式不符合要求：source中没有connect"
        assert "table" in source_key, "节点的格式不符合要求：source中没有table"
        target_key = self.target.keys()
        assert "connect" in target_key, "节点的格式不符合要求：target中没有connect"
        assert "database" in target_key, "节点的格式不符合要求：target中没有database"
        assert "table" in target_key, "节点的格式不符合要求：target中没有table"

    def connect(self) -> dict:
        self.LOG.info("开始连接")
        source_connect = self.temp_db.get_sql(self.source["connect"])
        target_connect = self.temp_db.get_nosql(self.target["connect"])[self.target["database"]]
        if "schema" in self.source.keys():
            source_sql = text("select * from " + self.source["schema"] + "." + self.source["table"])
        else:
            source_sql = text("select * from " + self.source["table"])
        return {
            "source_connect":source_connect, 
            "target_connect":target_connect, 
            "source_sql":source_sql
        }

    def read(self, source_sql: str, source_connect: sqlalchemy.Connection) -> dict:
        try:
            self.LOG.info("正在执行sql:" + str(source_sql))
            data = pd.read_sql_query(source_sql, source_connect)
            for col_name in data.columns:
                data[[col_name]] = data[[col_name]].astype(object).where(data[[col_name]].notnull(), None)
            self.LOG.info("数据形状为: " + str(data.shape[0]) + "," + str(data.shape[1]))
            return {
                "data":data, 
                "data_size":data.shape[0] * data.shape[1]
            }
        except:
            self.LOG.error(traceback.format_exc())
            self.LOG.info("正在回滚")
            source_connect.rollback()
        finally:
            source_connect.close()
        return {
                "data": None, 
                "data_size": 0
            }

    def write(self, data: pd.DataFrame, target_connect: pymongo.database.Database) -> None:
        try:
            self.LOG.info("正在清空表:" + self.target["table"])
            target_connect[self.target["table"]].drop()
            self.LOG.info("正在写入表:" + self.target["table"])
            data = data.to_dict('records')
            target_connect[self.target["table"]].insert_many(data)
        except:
            self.LOG.error(traceback.format_exc())


class excel_to_table(node_base):
    allow_type = ["excel_to_table", "csv_to_table"]
    def __init__(self, node_define: dict) -> None:
        super().__init__(node_define["name"], node_define["next_name"], db_engine, node_define["type"])
        self.source: dict = node_define["source"]
        self.target: dict = node_define["target"]
        self.data: pd.DataFrame|None = None
        # 检查节点格式是否符合要求
        source_key = self.source.keys()
        assert "path" in source_key, "节点的格式不符合要求：source中没有path"
        target_key = self.target.keys()
        assert "connect" in target_key, "节点的格式不符合要求：target中没有connect"
        assert "table" in target_key, "节点的格式不符合要求：target中没有table"

    def connect(self) -> dict:
        self.LOG.info("开始连接")
        target_connect = self.temp_db.get_sql(self.target["connect"])
        return {
            "source_connect":None, 
            "target_connect":target_connect, 
            "source_sql":""
        }
        
    def read(self, source_sql, source_connect) -> dict:
        try:
            if self.type == "excel_to_table":
                self.LOG.info("正在获取:" + self.source["path"] + "的" + self.source["sheet"])
                data = pd.read_excel(os.path.join(TABLE_PATH, self.source["path"]), sheet_name=self.source["sheet"], dtype=object)
            elif self.type == "csv_to_table":
                self.LOG.info("正在获取:" + self.source["path"])
                data = pd.read_csv(os.path.join(TABLE_PATH, self.source["path"]), dtype=object)
            self.LOG.info("数据形状为: " + str(data.shape[0]) + "," + str(data.shape[1]))
            return {
                "data":data, 
                "data_size":data.shape[0] * data.shape[1]
            }
        except:
            self.LOG.error(traceback.format_exc())
        return {
                "data": None, 
                "data_size": 0
            }

    def write(self, data: pd.DataFrame, target_connect: sqlalchemy.Connection) -> None:
        try:
            self.LOG.info("正在写入:" + self.target["table"])
            schema = self.target["schema"] if "schema" in self.target.keys() else None
            data.to_sql(name=self.target["table"], con=target_connect, schema=schema, index=False, if_exists='replace', chunksize=1000)
        except:
            self.LOG.error(traceback.format_exc())
            self.LOG.info("正在回滚")
            target_connect.rollback()
        finally:
            target_connect.close()

        

class excel_to_nosql(node_base):
    allow_type = ["excel_to_nosql", "csv_to_nosql"]
    def __init__(self, node_define: dict) -> None:
        super().__init__(node_define["name"], node_define["next_name"], db_engine, node_define["type"])
        self.source: dict = node_define["source"]
        self.target: dict = node_define["target"]
        self.data: pd.DataFrame|None = None
        # 检查节点格式是否符合要求
        source_key = self.source.keys()
        assert "path" in source_key, "节点的格式不符合要求：source中没有path"
        target_key = self.target.keys()
        assert "connect" in target_key, "节点的格式不符合要求：target中没有connect"
        assert "database" in target_key, "节点的格式不符合要求：target中没有database"
        assert "table" in target_key, "节点的格式不符合要求：target中没有table"

    def connect(self) -> dict:
        self.LOG.info("开始连接")
        target_connect = self.temp_db.get_nosql(self.target["connect"])[self.target["database"]]
        return {
            "source_connect":None, 
            "target_connect":target_connect, 
            "source_sql":""
        }
        
    def read(self, source_sql, source_connect) -> dict:
        try:
            if self.type == "excel_to_nosql":
                self.LOG.info("正在获取:" + self.source["path"] + "的" + self.source["sheet"])
                data = pd.read_excel(os.path.join(TABLE_PATH, self.source["path"]), sheet_name=self.source["sheet"], dtype=object)
            elif self.type == "csv_to_nosql":
                self.LOG.info("正在获取:" + self.source["path"])
                data = pd.read_csv(os.path.join(TABLE_PATH, self.source["path"]), dtype=object)
            for col_name in self.data.columns:
                data[[col_name]] = data[[col_name]].astype(object).where(data[[col_name]].notnull(), None)
            self.LOG.info("数据形状为: " + str(data.shape[0]) + "," + str(data.shape[1]))
            return {
                "data":data, 
                "data_size":data.shape[0] * data.shape[1]
            }
        except:
            self.LOG.error(traceback.format_exc())
        return {
                "data": None, 
                "data_size": 0
            }

    def write(self, data: pd.DataFrame, target_connect: pymongo.database.Database) -> None:
        try:
            self.LOG.info("正在清空表:" + self.target["table"])
            target_connect[self.target["table"]].drop()
            self.LOG.info("正在写入表:" + self.target["table"])
            data = data.to_dict('records')
            target_connect[self.target["table"]].insert_many(data)
        except:
            self.LOG.error(traceback.format_exc())
        

class table_to_excel(node_base):
    allow_type = ["table_to_excel", "table_to_csv"]
    def __init__(self, node_define: dict) -> None:
        super().__init__(node_define["name"], node_define["next_name"], db_engine, node_define["type"])
        self.source: dict = node_define["source"]
        self.target: dict = node_define["target"]
        self.data: pd.DataFrame|None = None
        # 检查节点格式是否符合要求
        source_key = self.source.keys()
        assert "connect" in source_key, "节点的格式不符合要求：source中没有connect"
        assert "table" in source_key, "节点的格式不符合要求：source中没有table"
        target_key = self.target.keys()
        assert "path" in target_key, "节点的格式不符合要求：target中没有path"

    def connect(self) -> dict:
        self.LOG.info("开始连接")
        source_connect = self.temp_db.get_sql(self.source["connect"])
        if "schema" in self.source.keys():
            source_sql = text("select * from " + self.source["schema"] + "." + self.source["table"])
        else:
            source_sql = text("select * from " + self.source["table"])
        return {
            "source_connect":source_connect, 
            "target_connect":None, 
            "source_sql":source_sql
        }
        
    def read(self, source_sql: str, source_connect: sqlalchemy.Connection) -> dict:
        try:
            self.LOG.info("正在执行sql:" + str(source_sql))
            data = pd.read_sql_query(source_sql, source_connect)
            self.LOG.info("数据形状为: " + str(data.shape[0]) + "," + str(data.shape[1]))
            return {
                "data":data, 
                "data_size":data.shape[0] * data.shape[1]
            }
        except:
            self.LOG.error(traceback.format_exc())
            self.LOG.info("正在回滚")
            source_connect.rollback()
        finally:
            source_connect.close()
        return {
                "data": None, 
                "data_size": 0
            }

    def write(self, data: pd.DataFrame, target_connect) -> None:
        try:
            self.LOG.info("正在写入:" + self.target["path"])
            temp_path = os.path.join(TABLE_PATH, self.target["path"])
            if self.type == "table_to_excel":
                # 保留原有excel数据并追加
                with pd.ExcelWriter(temp_path) as writer:
                    data.to_excel(writer, sheet_name=self.target["sheet"], index=False)
            elif self.type == "table_to_csv":
                data.to_csv(temp_path, index=False)
        except:
            self.LOG.error(traceback.format_exc())
        
        
class json_to_nosql(node_base):
    allow_type = ["json_to_nosql"]
    def __init__(self, node_define: dict) -> None:
        super().__init__(node_define["name"], node_define["next_name"], db_engine, node_define["type"])
        self.source: dict = node_define["source"]
        self.target: dict = node_define["target"]
        self.data = None
        # 检查节点格式是否符合要求
        source_key = self.source.keys()
        assert "path" in source_key, "节点的格式不符合要求：source中没有path"
        target_key = self.target.keys()
        assert "connect" in target_key, "节点的格式不符合要求：target中没有connect"
        assert "database" in target_key, "节点的格式不符合要求：target中没有database"
        assert "table" in target_key, "节点的格式不符合要求：target中没有table"

    def connect(self) -> dict:
        self.LOG.info("开始连接")
        target_connect = self.temp_db.get_nosql(self.target["connect"])[self.target["database"]]
        return {
            "source_connect":None, 
            "target_connect":target_connect, 
            "source_sql":""
        }
        
    def read(self, source_sql: str, source_connect: sqlalchemy.Connection) -> dict:
        try:
            self.LOG.info("正在获取:" + os.path.join(JS_PATH, self.source["path"]))
            with open(os.path.join(JS_PATH, self.source["path"]), mode='r', encoding='utf-8') as file:
                data = json.load(file)
            return {
                "data":data, 
                "data_size":get_data_size(str(self.data))
            }
        except:
            self.LOG.error(traceback.format_exc())
        return {
                "data": None, 
                "data_size": 0
            }

    def write(self, data: dict, target_connect: pymongo.database.Database) -> None:
        try:
            self.LOG.info("正在清空表:" + self.target["table"])
            target_connect[self.target["table"]].drop()
            self.LOG.info("正在写入表:" + self.target["table"])
            target_connect[self.target["table"]].insert_many(data)
        except:
            self.LOG.error(traceback.format_exc())
        

        
class nosql_to_json(node_base):
    allow_type = ["nosql_to_json"]
    def __init__(self, node_define: dict) -> None:
        super().__init__(node_define["name"], node_define["next_name"], db_engine, node_define["type"])
        self.source: dict = node_define["source"]
        self.target: dict = node_define["target"]
        self.data = None
        # 检查节点格式是否符合要求
        source_key = self.source.keys()
        assert "connect" in source_key, "节点的格式不符合要求：source中没有connect"
        assert "database" in source_key, "节点的格式不符合要求：source中没有database"
        assert "table" in source_key, "节点的格式不符合要求：source中没有table"
        target_key = self.target.keys()
        assert "path" in target_key, "节点的格式不符合要求：target中没有path"

    def connect(self) -> dict:
        self.LOG.info("开始连接")
        source_connect = self.temp_db.get_nosql(self.source["connect"])[self.source["database"]]
        return {
            "source_connect":source_connect, 
            "target_connect":None, 
            "source_sql":""
        }
        
    def read(self, source_sql: str, source_connect: pymongo.database.Database) -> dict:
        try:
            self.LOG.info("正在获取:" + self.source["table"])
            data = source_connect[self.source["table"]].find().to_list()
            return {
                "data":data, 
                "data_size":get_data_size(str(self.data))
            }
        except:
            self.LOG.error(traceback.format_exc())
        return {
                "data": None, 
                "data_size": 0
            }

    def write(self, data: dict, target_connect: pymongo.database.Database) -> None:
        try:
            self.LOG.info("正在写入:" + os.path.join(JS_PATH, self.target["path"]))
            with open(os.path.join(JS_PATH, self.target["path"]), mode='w', encoding='utf-8') as file:
                file.write(str(data))
        except:
            self.LOG.error(traceback.format_exc())
        

        
class nosql_to_nosql(node_base):
    allow_type = ["nosql_to_nosql"]
    def __init__(self, node_define: dict) -> None:
        super().__init__(node_define["name"], node_define["next_name"], db_engine, node_define["type"])
        self.source: dict = node_define["source"]
        self.target: dict = node_define["target"]
        self.data = None
        # 检查节点格式是否符合要求
        source_key = self.source.keys()
        assert "connect" in source_key, "节点的格式不符合要求：source中没有connect"
        assert "database" in source_key, "节点的格式不符合要求：source中没有database"
        assert "table" in source_key, "节点的格式不符合要求：source中没有table"
        target_key = self.target.keys()
        assert "connect" in target_key, "节点的格式不符合要求：target中没有connect"
        assert "database" in target_key, "节点的格式不符合要求：target中没有database"
        assert "table" in target_key, "节点的格式不符合要求：target中没有table"

    def connect(self) -> dict:
        self.LOG.info("开始连接")
        source_connect = self.temp_db.get_nosql(self.source["connect"])[self.source["database"]]
        target_connect = self.temp_db.get_nosql(self.target["connect"])[self.target["database"]]
        return {
            "source_connect":source_connect, 
            "target_connect":target_connect, 
            "source_sql":""
        }
        
    def read(self, source_sql: str, source_connect: pymongo.database.Database) -> dict:
        try:
            self.LOG.info("正在获取:" + self.source["table"])
            # 查询时排除id字段
            data = source_connect[self.source["table"]].find({}, {'_id': 0})
            return {
                "data":data, 
                "data_size":get_data_size(str(self.data))
            }
        except:
            self.LOG.error(traceback.format_exc())
        return {
                "data": None, 
                "data_size": 0
            }
            

    def write(self, data: dict, target_connect: pymongo.database.Database) -> None:
        try:
            self.LOG.info("正在清空表:" + self.target["table"])
            target_connect[self.target["table"]].drop()
            self.LOG.info("正在写入表:" + self.target["table"])
            target_connect[self.target["table"]].insert_many(data)
        except:
            self.LOG.error(traceback.format_exc())
        
        
class nosql_to_table(node_base):
    allow_type = ["nosql_to_table"]
    def __init__(self, node_define: dict) -> None:
        super().__init__(node_define["name"], node_define["next_name"], db_engine, node_define["type"])
        self.source: dict = node_define["source"]
        self.target: dict = node_define["target"]
        self.data = None
        # 检查节点格式是否符合要求
        source_key = self.source.keys()
        assert "connect" in source_key, "节点的格式不符合要求：source中没有connect"
        assert "database" in source_key, "节点的格式不符合要求：source中没有database"
        assert "table" in source_key, "节点的格式不符合要求：source中没有table"
        target_key = self.target.keys()
        assert "connect" in target_key, "节点的格式不符合要求：target中没有connect"
        assert "table" in target_key, "节点的格式不符合要求：target中没有table"

    def connect(self) -> None:
        self.LOG.info("开始连接")
        source_connect = self.temp_db.get_nosql(self.source["connect"])[self.source["database"]]
        target_connect = self.temp_db.get_sql(self.target["connect"])
        return {
            "source_connect":source_connect, 
            "target_connect":target_connect, 
            "source_sql":""
        }
        
    def read(self, source_sql: str, source_connect: pymongo.database.Database) -> dict:
        try:
            self.LOG.info("正在获取:" + self.source["table"])
            data = source_connect[self.source["table"]].find().to_list()
            data = pd.read_json(data, orient="records")
            return {
                "data":data, 
                "data_size":get_data_size(str(self.data))
            }
        except:
            self.LOG.error(traceback.format_exc())
        return {
                "data": None, 
                "data_size": 0
            }

    def write(self, data: pd.DataFrame, target_connect: sqlalchemy.Connection) -> None:
        try:
            self.LOG.info("正在写入:" + self.target["table"])
            schema = self.target["schema"] if "schema" in self.target.keys() else None
            data.to_sql(name=self.target["table"], con=target_connect, schema=schema, index=False, if_exists='replace', chunksize=1000)
        except:
            self.LOG.error(traceback.format_exc())
            self.LOG.info("正在回滚")
            target_connect.rollback()
        finally:
            target_connect.close()