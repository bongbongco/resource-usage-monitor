import psutil
import sqlite3
import threading
from functools import wraps
import os
import time
import argparse

collect_data = []
thread_count = 0

class ReportManager:
    def __init__(self):
        self.DatabaseManager = DatabaseManager()

    def create_csv(self):
        cell = ""

        all_data = self.DatabaseManager.get_all_data()
        csv_file = open("process_{}.csv".format(time.strftime("%Y-%m-%d")), 'a')
        
        for row in all_data:
            for index in range(1,11):
                cell = cell + str(row[index])+','
            cell = cell + '\n'
            csv_file.write(cell)
            cell = ""
        csv_file.close()

    def create_graph(self):
        pass


class SingletonInstane:
  __instance = None

  @classmethod
  def __getInstance(cls):
    return cls.__instance

  @classmethod
  def instance(cls, *args, **kargs):
    cls.__instance = cls(*args, **kargs)
    cls.instance = cls.__getInstance
    return cls.__instancee


class DatabaseManager(SingletonInstane):
    def __init__(self):
        self.database_name = "process_{}.db".format(time.strftime("%Y-%m-%d"))
        self.connect = None
        self.cursor = None

        self.name = None
        self.cpu_percent = None
        self.cpu_user_times = None
        self.cpu_system_times = None
        self.memeory = None
        self.read_count = None
        self.write_count = None
        self.read_bytes = None
        self.write_bytes = None
        
        self.checked_database()

    def checked_database(self):
        if not os.path.exists(self.database_name):
            self.create_database()
            self.create_table()

    def _connect_process_data(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.connect = sqlite3.connect(self.database_name, isolation_level = None)
            self.cursor = self.connect.cursor()
            return func(self, *args, **kwargs)
        return wrapper

    def _close_process_data(self):
        self.connect.commit()
        self.connect.close()

    @_connect_process_data
    def execute(self, sql, mode):
        self.cursor.execute(sql)
        if mode == "get":
            rows = self.cursor.fetchall()
            self._close_process_data()
            return rows

        elif mode == "set":
            self._close_process_data()
    
    @_connect_process_data
    def create_database(self):
        print "Ready to monitoring process"
        self._close_process_data()

    @_connect_process_data
    def create_table(self):
        sql = "create table if not exists process (\
        id integer PRIMARY KEY,\
        name text NOT NULL,\
        cpu_percent text NOT NULL,\
        cpu_user_times text NOT NULL,\
        cpu_system_times text NOT NULL,\
        memory text NOT NULL,\
        read_count text NOT NULL,\
        write_count text NOT NULL,\
        read_bytes text NOT NULL,\
        write_bytes text NOT NULL,\
        Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP\
        );"
        self.execute(sql, "set")

    def set_process_data(self):
        sql = "insert into process (name,\
        cpu_percent,\
        cpu_user_times,\
        cpu_system_times,\
        memory,\
        read_count,\
        write_count,\
        read_bytes,\
        write_bytes) values ('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(
                self.name,
                self.cpu_percent,
                self.cpu_user_times,
                self.cpu_system_times,
                self.memory,
                self.read_count,
                self.write_count,
                self.read_bytes,
                self.write_bytes)
        self.execute(sql,"set")

    def get_name(self):
        pass
    
    def get_cpu(self):
        pass

    def get_memory(self):
        pass

    def get_disk_read_count(self):
        pass

    def get_disk_write_count(self):
        pass

    def get_disk_read_bytes(self):
        pass

    def get_disk_write_bytes(self):
        pass
    
    def get_all_data(self):
        sql = "select * from process"
        return self.execute(sql, "get")

    def classify(self, unstructured_data):
        self.name = unstructured_data["name"]
        self.cpu_percent = unstructured_data["cpu_percent"]
        self.cpu_user_times = unstructured_data["cpu_user_times"]
        self.cpu_system_times = unstructured_data["cpu_system_times"]
        self.memory = unstructured_data["memory"]
        self.read_count = unstructured_data["read_count"]
        self.write_count = unstructured_data["write_count"]
        self.read_bytes = unstructured_data["read_bytes"]
        self.write_bytes = unstructured_data["write_bytes"]

    def working(self, data):
        self.checked_database()
        for unstructured_row in data:
            self.classify(unstructured_row)
            self.set_process_data()


class ProcessManager:
    def __init__(self, pid):
        self.pid = pid
        self.process = psutil.Process(self.pid)
        self.name = None
        self.cpu_percent = None
        self.cpu_user_times = None
        self.cpu_sysetem_times = None
        self.memory = None
        self.io = None

    def get_name(self):
        self.name = self.process.name()

    def get_cpu_percent(self):
        self.cpu_percent = self.process.cpu_percent(interval=1.0)

    def get_cpu_times(self):
        self.cpu_times = self.process.cpu_times()

    def get_memory(self):
        self.memory = self.process.memory_percent()

    def get_disk_io(self):
        self.io = self.process.io_counters()

    def get_summary(self):
        return {"name":self.name,
                "cpu_percent":self.cpu_percent,
                "cpu_user_times":self.cpu_times[0],
                "cpu_system_times":self.cpu_times[1],
                "memory":self.memory,
                "read_count":self.io[0],
                "write_count":self.io[1],
                "read_bytes":self.io[2],
                "write_bytes":self.io[3]}

    def working(self):
        self.get_name()
        self.get_cpu_percent()
        self.get_cpu_times()
        self.get_memory()
        self.get_disk_io()

        return self.get_summary()


class Secretary:
    def __init__(self):
        self.target = None
        self.targets = None
        self.system_idle_process = None
        self.ProcessManager = None
        self.process_data = [] 
        self.DatabaseManager = DatabaseManager()
        self.limit_time = 300
        self.work_time = time.time()
        self.start_time = time.time()
        self.interval = 5

        self.lock = threading.Lock()
        self.target_count = 0

        self.ReportManager = ReportManager()


    def get_processes(self):
        self.targets = psutil.pids()
        self.target_count = len(self.targets)

    def get_process_data(self):
        global collect_data
        global thread_count 

        self.process_data = self.ProcessManager.working()
        self.lock.acquire()
        collect_data.append(self.process_data)
        thread_count = thread_count + 1 
        self.lock.release()

    def set_process_data(self):
        self.DatabaseManager.working(self.process_data)

    def save_data(self):
        self.get_process_data()
        self.set_process_data()

    def write_report(self):
        self.ReportManager.create_csv()

    def checked_collect_time(self):
        if time.time() - self.work_time >= self.interval:
            self.work_time = time.time()
        else:
            time.sleep(0.2)

    def checked_limit_time(self):
        if time.time() - self.start_time >= self.limit_time:
            return True 

    def working(self):
        global collect_data
        global thread_count

        self.get_processes()

        for self.target in self.targets:
            try:
                self.ProcessManager = ProcessManager(self.target)
                
                get_thread = threading.Thread(target=self.get_process_data)
                get_thread.setDaemon(0)
                get_thread.start()

            except psutil.NoSuchProcess:
                print "terminated target process"
                thread_count = thread_count + 1
        
        while True: 
            print "total: {}, now: {}".format(self.target_count, thread_count)
            if thread_count == self.target_count: 
                self.process_data = collect_data
                self.set_process_data()
                thread_count = 0
                collect_data = []
                break
            else:
                continue

    def start(self):
        while True:
            self.checked_collect_time()
            self.working()
            if self.checked_limit_time():
                break
        
        print "Complete collecting process data"
        print
        print self.DatabaseManager.get_all_data()


def main():
    secretary = Secretary()
    secretary.start()

    #secretary.write_report()


if __name__=="__main__":
	main()
