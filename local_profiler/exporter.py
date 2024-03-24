import time
import os
from prometheus_client import Gauge
from prometheus_client import start_http_server
import re
from collections import deque
import argparse
import yaml
import utils.utility as utils
import utils.dyn_runner as dyn_runner
import threading
from collections import defaultdict

class my_exporter():
	def __init__(self, port, configs) -> None:
		self.g = Gauge(configs["metric_name"], configs["description"], ["funcname"])
		self.configs = configs
		self.port = port
		start_http_server(int(self.port))
		return

	@classmethod
	def clear(cls, res_path):
		#clear result file
		os.system(f'cat /dev/null > {res_path}')

	@classmethod
	def update_gauge(cls, gauge, res_path):
		with open(res_path, "r") as f:
			lines = f.readlines()
			for line in lines:
				line = line.split()
				gauge.labels(line[3]).set(line[1])
		return

	def stop_running_profiler_java(self, pid):
		os.system(f"bash ./java_profiler/profiler.sh stop {pid} > /dev/null")

	def process_res(self, lang, res_path):
		funcs_count = aggregate_traces(lang, res_path)
  
		update_Prometheus_metric(funcs_count, self.g, self.configs["tracked_funcs"])
		return
	
	def run_multi_exporter(self, pids, lang):
		res_path = f"./file/gen_tmp"
		if self.configs["option"]["freq"] == "dynamic":
			runner = dyn_runner.DynRunner(self.configs["dur"], 10, 0.5)
			while(True):
				threads = []
				now_freq = runner.nowFreq
				for pid in pids:
					t = threading.Thread(target=self.prof_single_round, args=(pid, res_path, lang, now_freq))
					t.start()
					threads.append(t)

				for t in threads:
					t.join()

				self.process_res(lang, res_path)

				thisRunFuncs = dyn_runner.readCollapsed(res_path, runner.topn)

				runner.lastFreq = runner.nowFreq
				runner.nowFreq = runner.adjFreq(runner.lastRunFuncs, thisRunFuncs)
				runner.lastRunFuncs = thisRunFuncs
				time.sleep(self.configs["option"]["wait_time"])
		else:
			while(True):
				threads = []
				freq = self.configs["option"]["freq"]
				for pid in pids:
					t = threading.Thread(target=self.prof_single_round, args=(pid, res_path, lang, freq))
					t.start()
					threads.append(t)

				for t in threads:
					t.join()

				self.process_res(lang, res_path)
				time.sleep(self.configs["option"]["wait_time"])
		return

	#topn: only record the top n highest metrics
	#wait_time: wait for some secs after exporter sends info
	res_sema = threading.Semaphore(1)
	def prof_single_round(self, pid, res_path, lang, freq):
		tmp_path = f"./file/{pid}_tmp"
		if lang=="java":
			itv = int(1000*1000/freq)
			cmd = f"bash ./java_profiler/profiler.sh -o collapsed -g -l -i {itv}  -d {self.configs["dur"]}  --fdtransfer {pid} > {tmp_path}"
		elif lang=="python":
			cmd = f"bash ./python_profiler/py-spy record -f raw -r {freq} -o {tmp_path} -p {pid}"
		else:
			pass

		res_dir = os.path.dirname(res_path)
		if not os.path.exists(res_dir):
			os.makedirs(res_dir)
		my_exporter.clear(res_path)

		try:
			os.system(cmd)
		except Exception as err:
			return err
		
		my_exporter.res_sema.acquire()
  
		with open(tmp_path, "r") as src, open(res_path, "a") as tgt:
			content = src.read()
			tgt.write(content)
   
		my_exporter.res_sema.release()

		os.remove(tmp_path)
		return


def aggregate_traces(language, res_path):
	if(language == "java"):
		funcs_count  = proc_res_java(res_path)
	elif(language == "python"):
		funcs_count = proc_res_python(res_path)
	return funcs_count

def proc_res_java(res_path):
	funcsCount = defaultdict(int)
	with open(res_path, "r") as f:
		for line in f.readlines():
			line = line.strip()
			funcs = line.split(";")
			func_name = funcs[-1][:funcs[-1].rfind(" ")]
			count = int(funcs[-1][funcs[-1].rfind(" ")+1:])
			funcsCount[func_name] += count
	return funcsCount

def proc_res_python(res_path):
	funcs_count = defaultdict(int)
	with open(res_path) as f:
		for line in f:
			line = line.strip()
			funcs = line.split(";")
			idx = funcs[-1].index(")")+1
			func = funcs[-1][:idx]
			count = int(funcs[-1][idx:])
			funcs_count[func] += count
	return funcs_count

def update_Prometheus_metric(funcs_count, gauge, topn_a=10):
	topn_keys = utils.get_topn_keys(funcs_count, lambda x:x[1].time, topn_a)
	aggregrated_cpu_time = utils.update_dict(aggregrated_cpu_time, topn_keys)
	for key in aggregrated_cpu_time:
		agg_metric = aggregrated_cpu_time[key]
		gauge.labels(agg_metric.name).set(agg_metric.time)
	return

