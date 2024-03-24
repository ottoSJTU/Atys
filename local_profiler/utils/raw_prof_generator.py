import argparse
import yaml
import os

class raw_prof_generator():
    def __init__(self, configs, pid, lang):
        self.configs = configs
        self.pid = pid
        self.lang = lang
        return
    
    def gen_collapsed(self):
        def stop_running_profiler_java(pid):
            os.system(f"bash ./java_profiler/profiler.sh stop {pid} > /dev/null")
        
        res_path = f"./file/{self.pid}/tmp"
        
        if(self.lang=="java"):
            #action = configs["action"]
            action = "collect"
            option = self.configs["option"]

            stop_running_profiler_java(self.pid)
            prof_cmd = f"bash ./java_profiler/profiler.sh {action} -o collapsed -g -a -t -l {option} {self.pid} > {res_path}"
            os.system(prof_cmd)

        elif(self.lang=="python"):
            action = "record"
            option = self.configs["option"]

            prof_cmd = f"./python_profiler/py-spy {action} {option} -f raw -F -t --native -o {res_path} -p {self.pid}"
            os.system(prof_cmd)
            
        return
    

