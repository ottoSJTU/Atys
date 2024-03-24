from flask import Flask, request, abort, jsonify
from functools import wraps
from utils import raw_prof_generator
import utils.utility as utils
import os
import time
import docker
from exporter import my_exporter

app = Flask(__name__)
API_KEY = "passwd"
ROOT_PASSWORD = "k8smaster"
#{service_name: [pids]}
RUNNING_TASKS = {}
	
def require_api_key(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		api_key = request.headers.get('X-API-KEY')
		if api_key != API_KEY:
			abort(403)  
		return f(*args, **kwargs)
	return decorated_function

@app.route('/profile')
@require_api_key
def profile():
	configs = request.json["configs"]
	service = configs["service_name"]
	type = configs["type"]
	pids, lang = utils.find_pid_by_process_name(service)
	try:
		if lang == "java":
			if type == "process":
				port = run_exporter(pids, configs, lang)
			elif type == "container":
				local_profiler_dir = utils.exec("pwd")
				local_lib_dir = os.path.join(local_profiler_dir, "java_profiler/build/")
				client = docker.from_env()
				def get_container_by_pid(pid):
					for container in client.containers.list():
						container_pid = container.attrs['State']['Pid']
						if container_pid == pid:
							return container
					return None
				
				for pid in pids:
					container_id = get_container_by_pid(pid)
					utils.exec(f'echo {ROOT_PASSWORD} | sudo -S bash pre_container.sh {container_id} {local_lib_dir}')
				port = run_exporter(pids, configs, lang)

		elif lang=="python":
			port = run_exporter(pids, configs, lang)
	except:
		abort(400)

	if service in RUNNING_TASKS:
		for pid in pids:  RUNNING_TASKS[service].append(pid)
	else: RUNNING_TASKS[service] = pids

	return jsonify({"port": port})

@app.route('/control')
@require_api_key
def control():
	action = request.headers.get("ACT")
	try:
		if action=="list":
			return jsonify({"tasks":RUNNING_TASKS})
		elif action=="stop":
			service_name = request.json["service_name"]
			service_pids, _ = utils.find_pid_by_process_name(service_name)
			profile_pids = []
			for pid in service_pids:
				profile_pids.append(utils.find_matching_processes(pid))
			utils.kill_processes(profile_pids)
			return
	except:
		abort(400)

@app.route('/flamegraph')  
@require_api_key
def flamegraph():
	try:
		configs = request.json["configs"]
		service_name = configs["service_name"]
		pids, lang = utils.find_pid_by_process_name(service_name)
		for pid in pids:
			generator = raw_prof_generator.raw_prof_generator(configs, pid, lang)
			generator.gen_collapsed()
			file_to_send = f"./file/{pid}/tmp"
			utils.send_file(file_to_send)
	except: abort(400)
	return 

def run_exporter(pids, configs, lang):
	port = utils.get_free_port()
	exporter = my_exporter(port, configs)
	exporter.run_multi_exporter(pids, lang)
	return port

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5566)
