from typing import Iterable
import xmlrpc.client
import base64
import socket
import subprocess
from contextlib import closing
import psutil
import signal
import os

def get_topn_keys(iter:Iterable, key, topn:int):
    lst = sorted(iter, key=key, reverse=True)
    try:
        topn_lst = lst[:topn]
    except:
        topn_lst = lst
    topn_keys = [key for key, value in topn_lst]
    return topn_keys

def update_dict(tar, keys):
    tar = {key: value for key, value in tar.items() if key in keys}
    return tar

def send_file(filepath):
    proxy = xmlrpc.client.ServerProxy("http://localhost:8000/")
    with open(filepath, 'rb') as f:
        file_data = f.read()
    # 编码文件数据
    encoded_file_data = base64.b64encode(file_data).decode('utf-8')
    filename = filepath.split('/')[-1]
    result = proxy.receive_file(encoded_file_data, filename)
    print(result)

def get_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
    
def exec(cmd):
	res = subprocess.run(f"ps -ef | grep {cmd} | grep -v grep", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True).stdout
	return res

def find_pid_by_process_name(service_name):
	langs = ["python", "java"]
	target_lang = "compiled"
	pids = []

	cmd = "ps -ef | grep {service_name} | grep -v grep"
	res = exec(cmd)
	for line in res.strip().split("\n"):
		if(line.find(service_name) >= 0):
			pids.append(line.split()[1])
		for lang in langs:
			#print(line.split())
			if(line.split()[-2].split("/")[-1]==lang): target_lang = lang

	return pids, target_lang

def checkPid(pid):
	process_dir = os.path.join('/proc', str(pid))
	return(os.path.exists(process_dir))

def find_matching_processes(pid):
    target_scripts = ['bash ./java_profiler/profiler.sh', 'bash ./python_profiler/py-spy']
    for proc in psutil.process_iter(attrs=['pid', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'])
            if any(script in cmdline for script in target_scripts) and str(pid) in cmdline:
                matching_pid = proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return matching_pid

def kill_processes(pid_list):
    for pid in pid_list:
        try:
            # 发送SIGTERM信号
            os.kill(pid, signal.SIGTERM)
            print(f"Process with PID {pid} has been terminated")
        except OSError as e:
            print(f"Unable to terminate process with PID {pid}: {e}")