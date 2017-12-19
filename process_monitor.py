import psutil
import sqlite3
import threading
from functools import wraps
import os
import time
import datetime
import argparse
import xlsxwriter

collect_data = []
thread_count = 0


class ReportManager:
    def __init__(self, export_path):
        self.export_path = export_path
        self.DatabaseManager = DatabaseManager(self.export_path)
        self.workbook = None 
        self.worksheet = None
      
        self.title_format = None
        self.name_format = None
        self.index_format = None
        self.content_format = None

        self.name = ''
        self.index = 0
        self.column = 'A'
        self.width = 5
        self.items = None
    
        self.time = time.strftime("%Y-%m-%d")

    def create_csv(self):
        cell = "name,cpu_percent,cpu_user_times,cpu_system_times,memory,read_count,write_count,read_bytes,write_bytes,loop,monitor_time,timestamp(UTC)\n"

        all_data = self.DatabaseManager.get_all_data()
        csv_file = open("{}\\process_{}.csv".format(self.export_path, self.time), 'a')
        
        for row in all_data:
            for index in range(1,13):
                cell = cell + str(row[index])+','
            cell = cell[:-1] + '\n'
            csv_file.write(cell)
            cell = ""
        csv_file.close()

    def create_xl(self):
        self.workbook = xlsxwriter.Workbook("{}\\summary_report_{}.xlsx".format(self.export_path, self.time))
        self.worksheet = self.workbook.add_worksheet("Summary_{}".format(self.time))

        self.set_format()

        self.set_title()
        self.set_index()

        self.get_cpu_percent_rank() 
        self.set_cpu_percent_rank()

        self.get_memory_rank()
        self.set_memory_rank()

        self.get_read_rank()
        self.set_read_rank()

        self.get_write_rank()
        self.set_write_rank()

        self.workbook.close()

    def set_format(self):
        self.title_format = self.workbook.add_format({'font_size':15, 
            'align':'center', 
            'valign':'vcenter', 
            'border':1, 
            'bg_color':'gray', 
            'font_color':'white'})
        self.name_format = self.workbook.add_format({'bold':True, 
            'align':'center', 
            'valign':'vcenter', 
            'border':1, 
            'bg_color':'gray', 
            'font_color':'white'})
        self.index_format = self.workbook.add_format({'align':'center', 
            'valign':'vcenter', 
            'border':1})
        self.content_format = self.workbook.add_format({'valign':'vcenter', 
            'border':1}) 

    def set_title(self):
        self.worksheet.merge_range('B2:F2', "TOP 15 Process", self.title_format)

    def set_index(self):
        self.index = 3
        self.column = 'B'
        self.name = "Idx"
        self.width = 5

        index = []
        for i in range(1, 16):
            index.append([i])
        
        self.items = index
        self.worksheet.set_column('{0}:{0}'.format('A'), 2) 
        self.worksheet.set_column('{0}:{0}'.format(self.column), self.width)
        self.worksheet.write('{}{}'.format(self.column, self.index), self.name, self.name_format)
        self.index = self.index + 1
        
        for item in self.items:
            self.worksheet.write('{}{}'.format(self.column, self.index), item[0], self.index_format)
            self.index = self.index + 1

    def set_cpu_percent_rank(self):
        self.index = 3 
        self.column = 'C'
        self.width = 33
        self.name = "CPU Percent" 
        self.write_data()

    def get_cpu_percent_rank(self):
        self.items = self.DatabaseManager.get_cpu_percent_rank()

    def set_memory_rank(self):
        self.index = 3
        self.column = 'D'
        self.width = 33
        self.name = "Memory"
        self.write_data()

    def get_memory_rank(self):
        self.items = self.DatabaseManager.get_memory_rank()

    def set_read_rank(self):
        self.index = 3
        self.column = 'E'
        self.width = 33
        self.name = "Read"
        self.write_data()

    def get_read_rank(self):
        self.items = self.DatabaseManager.get_read_count_rank()

    def set_write_rank(self):
        self.index = 3
        self.column = 'F'
        self.width = 33
        self.name = "Write"
        self.write_data()

    def get_write_rank(self):
        self.items = self.DatabaseManager.get_write_count_rank()

    def write_data(self):
        self.worksheet.set_column('{0}:{0}'.format(self.column), self.width)
        self.worksheet.write('{}{}'.format(self.column, self.index), self.name, self.name_format)
        self.index = self.index + 1
        
        for item in self.items:
            self.worksheet.write('{}{}'.format(self.column, self.index), item[0], self.content_format)
            self.index = self.index + 1


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
    def __init__(self, export_path):
        self.export_path = export_path
        self.database_name = "{}\\process_{}.db".format(self.export_path, time.strftime("%Y-%m-%d"))
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
        self.loop = None
        self.monitor_time = None

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
        loop text NOT NULL,\
        monitor_time text NOT NULL,\
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
        write_bytes,\
        loop,\
        monitor_time) values ('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(
                self.name,
                self.cpu_percent,
                self.cpu_user_times,
                self.cpu_system_times,
                self.memory,
                self.read_count,
                self.write_count,
                self.read_bytes,
                self.write_bytes,
                self.loop,
                self.monitor_time)
        self.execute(sql,"set")

    def get_write_count_rank(self):
        sql = "select distinct name from process order by write_count DESC Limit 15;"
        return self.execute(sql, "get")

    def get_read_count_rank(self):
        sql = "select distinct name from process order by read_count DESC Limit 15;"
        return self.execute(sql, "get")

    def get_cpu_percent_rank(self):
        sql = "select distinct name from process order by cpu_percent DESC Limit 15;"
        return self.execute(sql, "get")

    def get_memory_rank(self):
        sql = "select distinct name from process order by memory DESC Limit 15;"
        return self.execute(sql, "get")

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
        self.loop = unstructured_data["loop"]
        self.monitor_time = unstructured_data["monitor_time"]

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
        self.cpu_percent = self.process.cpu_percent()

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
    def __init__(self, export_path, interval, limit_time, debug, report, csv):
        self.target = None
        self.targets = None
        self.ProcessManager = None
        self.process_data = [] 
        
        self.limit_time = limit_time * 60
        self.work_time = time.time()
        self.start_time = time.time()
        self.interval = interval
        self.loop = 0
        self.lock = threading.Lock()
        self.target_count = 0
        self.debug_mode = debug
        
        self.DatabaseManager = DatabaseManager(export_path)
       
        self.ReportManager = ReportManager(export_path)
        self.report = report
        self.csv = csv

    def _check_times(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            while True:
                if time.time() - self.work_time >= self.interval or self.loop == 0:
                    self.work_time = time.time()
                    self.loop = self.loop + 1
                    return func(self, *args, **kwargs)
                else:
                    time.sleep(0.2)
        return wrapper

    def get_processes(self):
        self.targets = psutil.pids()
        self.target_count = len(self.targets)

    def get_process_data(self):
        global collect_data
        global thread_count 

        self.process_data = self.ProcessManager.working()
        self.process_data.update({"loop":self.loop})
        self.process_data.update({"monitor_time":time.strftime("%Y-%m-%d %H:%M:%S")})
        self.lock.acquire()
        collect_data.append(self.process_data)
        thread_count = thread_count + 1 
        self.lock.release()

    def set_process_data(self):
        self.DatabaseManager.working(self.process_data)

    def write_document(self):
        if self.csv:
            self.ReportManager.create_csv()
        
        if self.report:
            self.ReportManager.create_xl()

    def checked_limit_time(self):
        if time.time() - self.start_time >= self.limit_time:
            return True 
        else:
            return False
    
    @_check_times
    def working(self):
        global collect_data
        global thread_count
        waiting_count = 0

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
            if self.debug_mode:
                self.debug()
            if thread_count == self.target_count or waiting_count >= 10: 
                self.process_data = collect_data
                self.set_process_data()
                thread_count = 0
                collect_data = []
                break
            else:
                waiting_count = waiting_count + 1
                time.sleep(0.2)
                continue

    def debug(self):
        print "loop: {}, total: {}, now: {}, time: {}".format(self.loop, 
                self.target_count, 
                thread_count,
                time.strftime("%Y-%m-%d %H:%M:%S"))

    def start(self):
        while True:
            self.working()

            if self.checked_limit_time():
                break
        
        if self.report or self.csv:
            self.write_document()
        
        print "Complete collecting process data"
        print "loop count: {}, start time: {}, end time: {}".format(self.loop, 
                datetime.datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S"),
                time.strftime("%Y-%m-%d %H:%M:%S"))


def main():
    parser = argparse.ArgumentParser()
  
    parser.add_argument("-p", "--path", default=".", help="path to export data", type=str)
    parser.add_argument("-i", "--interval", default=5, help="interval to collect data (sec)", type=int)
    parser.add_argument("-t", "--time", default=5, help="time to collect data (min)", type=int)
    parser.add_argument("-d", "--debug", default=0, help="debug mode (on: 1, off: 0)", type=int)
    parser.add_argument("-r", "--report", default=1, help="create summary report", type=int)
    parser.add_argument("-c", "--csv", default=1, help="create csv", type=int)

    args = parser.parse_args()
    
    secretary = Secretary(args.path, args.interval, args.time, args.debug, args.report, args.csv)
    
    secretary.start()

if __name__=="__main__":
	main()
