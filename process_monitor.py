import psutil
import sqlite3
import threading
from functools import wraps
import os
import time
import datetime
import argparse
import xlsxwriter
import platform

collect_data = []
thread_count = 0
export_path = ""


class DocumentManager:
    def __init__(self):
        global export_path
        self.export_path = export_path
        self.AnalysisManager = AnalysisManager()

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
        self.items = []
    
        self.time = time.strftime("%Y-%m-%d")
        
    def create_csv(self):
        cell = "name,\
        cpu_percent,\
        cpu_user_times,\
        cpu_system_times,\
        memory,\
        read_count,\
        write_count,\
        read_bytes,\
        write_bytes,\
        loop,\
        monitor_time,\
        timestamp(UTC)\n"

        all_data = self.AnalysisManager.get_all_data()
        csv_file = open("{}\\{}_process_{}.csv".format(self.export_path, 
            platform.node(), 
            self.time), 'a')
        
        for row in all_data:
            for index in range(1,13):
                cell = cell + str(row[index])+','
            cell = cell[:-1] + '\n'
            csv_file.write(cell)
            cell = ""
        csv_file.close()

    def create_xl(self):
        self.workbook = xlsxwriter.Workbook("{}\\{}_summary_report_{}.xlsx".format(self.export_path, 
            platform.node(),
            self.time))
        self.worksheet = self.workbook.add_worksheet("Summary_{}_{}".format(platform.node(), 
            self.time))

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
        self.items = self.AnalysisManager.get_cpu_percent_rank()

    def set_memory_rank(self):
        self.index = 3
        self.column = 'D'
        self.width = 33
        self.name = "Memory"
        self.write_data()

    def get_memory_rank(self):
        self.items = self.AnalysisManager.get_memory_rank()

    def set_read_rank(self):
        self.index = 3
        self.column = 'E'
        self.width = 33
        self.name = "Read"
        self.write_data()

    def get_read_rank(self):
        self.items = self.AnalysisManager.get_read_count_rank()

    def set_write_rank(self):
        self.index = 3
        self.column = 'F'
        self.width = 33
        self.name = "Write"
        self.write_data()

    def get_write_rank(self):
        self.items = self.AnalysisManager.get_write_count_rank()

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


class AnalysisManager(SingletonInstane):
    def __init__(self):
        global export_path
        self.export_path = export_path
        self.dump_name = "{}\\{}_process_{}.sql".format(self.export_path, 
                platform.node(), 
                time.strftime("%Y-%m-%d"))
        self.database_name = "{}\\{}_process_{}.db".format(self.export_path, 
                platform.node(), 
                time.strftime("%Y-%m-%d"))

        self.connect = None
        self.cursor = None
        self.ready_to_dump = False

    def _connect_process_data(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.connect = sqlite3.connect("{}".format(self.database_name), isolation_level = None)
            self.cursor = self.connect.cursor()
            return func(self, *args, **kwargs)
        return wrapper
    
    def _check_database(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if os.path.exists(self.dump_name):
                self.ready_to_dump = True
            return func(self, *args, **kwargs)
        return wrapper

    def execute(self, sql):
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        self.connect.commit()
        self.connect.close()
        return rows

    @_check_database
    @_connect_process_data
    def create_database(self):
        if self.ready_to_dump:
            dump_file = open("{}".format(self.dump_name), 'r')
            sql = dump_file.read()
            self.connect.executescript(sql)
            self.connect.close()

    @_connect_process_data
    def get_write_count_rank(self):
        sql = "select distinct name from process order by write_count DESC Limit 15;"
        return self.execute(sql)

    @_connect_process_data
    def get_read_count_rank(self):
        sql = "select distinct name from process order by read_count DESC Limit 15;"
        return self.execute(sql)

    @_connect_process_data
    def get_cpu_percent_rank(self):
        sql = "select distinct name from process order by cpu_percent DESC Limit 15;"
        return self.execute(sql)

    @_connect_process_data
    def get_memory_rank(self):
        sql = "select distinct name from process order by memory DESC Limit 15;"
        return self.execute(sql)

    @_connect_process_data
    def get_all_data(self):
        sql = "select * from process"
        return self.execute(sql)


class CollectManager(SingletonInstane):
    def __init__(self):
        global export_path
        self.export_path = export_path
        self.dump_name = "{}\\{}_process_{}.sql".format(self.export_path, 
                platform.node(),
                time.strftime("%Y-%m-%d"))
        self.connect = sqlite3.connect("{}".format(":memory:"), check_same_thread = False)
        self.cursor = self.connect.cursor()

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

        self.create_table()
    
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
        self.cursor.execute(sql)

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
        monitor_time) values ('{}',\
        '{}',\
        '{}',\
        '{}',\
        '{}',\
        '{}',\
        '{}',\
        '{}',\
        '{}',\
        '{}',\
        '{}')".format(
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
       
        self.cursor.execute(sql)

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

    def dump(self):
        with open("{}".format(self.dump_name), 'w') as f:
            for line in self.connect.iterdump():
                f.write('%s\n' % line)
        self.connect.close()

    def working(self, data):
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
        global thread_count

        try:
            self.cpu_percent = self.process.cpu_percent(interval=0.1)
        except psutil.NoSuchProcess:
            print "terminated target process"
            thread_count = thread_count + 1

    def get_cpu_times(self):
        global thread_count

        try:
            self.cpu_times = self.process.cpu_times()
        except psutil.NoSuchProcess:
            print "terminated target process"
            thread_count = thread_count + 1 

    def get_memory(self):
        global thread_count

        try:
            self.memory = self.process.memory_percent()
        except psutil.NoSuchProcess:
            print "terminated target process"
            thread_count = thread_count + 1

    def get_disk_io(self):
        global thread_count

        try:
            self.io = self.process.io_counters()
        except psutil.NoSuchProcess:
            print "terminated target process"
            thread_count = thread_count + 1

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
    def __init__(self, export_path_, interval, limit_time, debug, report, csv):
        global export_path
        export_path = export_path_
        self.export_path = export_path_
        
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
        
        self.CollectManager = CollectManager()
       
        self.DocumentManager = DocumentManager()
        self.report = report
        self.csv = csv

        self.AnalysisManager = AnalysisManager()

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

    def checked_limit_time(self):
        if time.time() - self.start_time >= self.limit_time:
            return True 
        else:
            return False

    def get_processes(self):
        self.targets = psutil.pids()
        self.target_count = len(self.targets)

    def get_process_data(self):
        global collect_data
        global thread_count 

        process_data = self.ProcessManager.working()
        process_data.update({"loop":"{}".format(self.loop)})
        process_data.update({"monitor_time":"{}".format(time.strftime("%Y-%m-%d %H:%M:%S"))})

        self.lock.acquire()
        collect_data.append(process_data)
        thread_count = thread_count + 1 
        self.lock.release()

    def save_monitor_data(self):
        self.CollectManager.working(self.process_data)

    def monitor_work(self):
        monitor_thread = threading.Thread(target=self.get_process_data)
        monitor_thread.setDaemon(0)
        monitor_thread.start()

    def save_work(self):
        saving_thread = threading.Thread(target=self.save_monitor_data)
        saving_thread.setDaemon(0)
        saving_thread.start()

    def write_document(self):
        self.AnalysisManager.create_database()

        if self.csv:
            self.DocumentManager.create_csv()
        
        if self.report:
            self.DocumentManager.create_xl()

    def delete_dump(self):
        os.remove("{}\\{}_process_{}.sql".format(self.export_path, 
            platform.node(),
            time.strftime("%Y-%m-%d")))
    
    @_check_times
    def process_monitoring(self):
        global collect_data
        global thread_count

        waiting_count = 0

        self.get_processes()

        for self.target in self.targets:
            try:
                self.ProcessManager = ProcessManager(self.target)
                self.monitor_work()

            except psutil.NoSuchProcess:
                print "terminated target process"
                thread_count = thread_count + 1
        
        while True: 
            if self.debug_mode:
                self.debug()
            if thread_count == self.target_count or waiting_count >= 10: 
                self.process_data = collect_data
                self.save_work()
                thread_count = 0
                collect_data = []
                break
            else:
                waiting_count = waiting_count + 1
                time.sleep(0.1)
                continue

    def debug(self):
        global collect_data
        print "loop: {}, total: {}, now: {}, time: {}".format(self.loop, 
                self.target_count, 
                thread_count,
                time.strftime("%Y-%m-%d %H:%M:%S"))
        print collect_data

    def start(self):
        while True:
            self.process_monitoring()

            if self.checked_limit_time():
                break
        
        self.CollectManager.dump()

        if self.report or self.csv:
            self.write_document()

        self.delete_dump()
        
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
