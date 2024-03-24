import requests
import argparse
import os
from concurrent.futures import ThreadPoolExecutor
import yaml
from utils.flamegraph import gen_flamegraph
from xmlrpc.server import SimpleXMLRPCServer
import base64

NODE_PORT = 5566
API_KEY = "passwd"

class profiler_controller:
	def __init__(self, config_path= str):
		with open('nodes.yaml', 'r') as nd:
			self.nodes = yaml.load(nd.read(), Loader=yaml.SafeLoader)
		with open(config_path, "r", encoding='utf-8') as cf:
			self.configs = yaml.load(cf.read(), Loader=yaml.SafeLoader)
		self.reg_file_rec()

	def reg_file_rec(self):
		def receive_file(data, filename):
			file_data = base64.b64decode(data)
			with open(filename, 'wb') as f:
				f.write(file_data)
			return f"Received file: {filename}"

		server = SimpleXMLRPCServer(('localhost', 8000), allow_none=True)
		server.register_function(receive_file, "receive_file")
		server.serve_forever()

	def wait_for_cmd(self):
		while(True):
			action = input("""
					type \"run\" to start profiler and prometheus server;\n
					type \"flamegraph\" to generate global flamegraph;\n
					type \"list\" to show running tasks;\n
					type \"stop\" to stop profiling;\n
					type \"exit\" to exit program;\n
					command: """)
			prof_cmd = ["run", "flamegraph"]
			ctrl_cmd = ["list", "stop", "exit"]
			
			if(action in prof_cmd):
				head = {"TYPE": "prof", "ACT":action}
				request_data = {"configs":self.configs}
				if action == "run":
					for node in self.nodes:
						response = send_req(node+"/profile", head, request_data)
						if response.status_code == 200:
							response_data = response.json()
							port = response_data.get('port')
							add_prometheus_trace(node+":"+str(port), f"{self.configs["service_name"]} of {node}")
						else:
							print(f"Request failed with status code: {response.status_code}")
				elif action == "flamegraph":
					service_name = self.configs["service_name"]
					for node in self.nodes:
						response = send_req(node+"/flamegraph", head, request_data)
						if response.status_code == 200:
							print("done")
						else:
							print(f"Request failed with status code: {response.status_code}")
					res_dir = f"./file/FG/{service_name}"
					os.system(f"python ./utils/flamegraph/gen_flamegraph.py --in_dir {res_dir} --out_dir {res_dir}")
					print("done")

			elif(action in ctrl_cmd):
				head = {"TYPE": "control", "ACT":action}
				request_data = {}
				if(action == "list"):
					for node in self.nodes:
						response = send_req(node+"/control", head, request_data)
						if response.status_code == 200:
							response_data = response.json()
							tasks = response_data.get('tasks')
							print(tasks)
						else:
							print(f"Request failed with status code: {response.status_code}")

				elif(action == "stop"):
					node = input("nodes ip to be stopped(devided by " "), \"all\" to stop all tasks")
					service = input("services to be stopped(devided by " ")")
					if node=="all":
						for node in self.nodes:
							request_data = {"service_name":[service]}
							response = send_req(node+"/control", head, request_data)
							if response.status_code == 200:
								print(f"done from node {node}")
							else:
								print(f"Request failed with status code: {response.status_code}")
					else:
						request_data = {"service_name":[service]}
						response = send_req(node+"/control", head, request_data)
						if response.status_code == 200:
							print("done")
						else:
							print(f"Request failed with status code: {response.status_code}")

				elif(action == "exit"):
					exit(0)
			
			else:
				print("invalid command")
				
		return

def send_req(node, headers, data):
	url = node + "/" + NODE_PORT
	headers["X-API-KEY"] = API_KEY 
	response = requests.post(url, headers=headers, json=data)
	return response

def add_prometheus_trace(url, instance):
	prometheus_config_path = "/prometheus/prometheus.yml"
	with open(prometheus_config_path) as f:
		config = yaml.safe_load(f)

	if 'scrape_configs' in config:
		for job in config['scrape_configs']:
			if job.get('job_name') == 'prometheus':
				job['static_configs'][0]['targets'] = [url]
				job['static_configs'][0]['labels']['instance'] = instance
				break

	with open(prometheus_config_path, 'w') as f:
		yaml.safe_dump(config, f)
	return
	
if __name__=="__main__":
	#run sudo like session.run(f"echo {password} | sudo -S cmd ", pty=False, hide=True)
	parser = argparse.ArgumentParser()
	parser.add_argument("-c", "--config", help="path of configuration file")
	args = parser.parse_args()
	controller = profiler_controller(args.config)
	controller.wait_for_cmd()