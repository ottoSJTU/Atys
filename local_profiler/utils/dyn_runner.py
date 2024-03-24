from ordered_set import OrderedSet
from collections import OrderedDict, defaultdict
from scipy import stats
import numpy as np
import os

def readCollapsed(resPath, topn):
	topnFuncs = []
	funcsCount = defaultdict(int)
	with open(resPath, "r") as f:
		for line in f.readlines():
			line = line.strip()
			funcs = line.split(";")

			func_name = funcs[-1][:funcs[-1].rfind(" ")]
			count = int(funcs[-1][funcs[-1].rfind(" ")+1:])
			funcsCount[func_name] += count
	sortedKeys = sorted(funcsCount, key=funcsCount.get, reverse=True)
	for key in sortedKeys[:topn]:
		topnFuncs.append((key, funcsCount[key]))
	return topnFuncs

def calc_Js_Div(funcs1, funcs2):
	allFuncs = OrderedSet()
	allFuncs.update(func[0] for func in funcs1)
	allFuncs.update(func[0] for func in funcs2)
	
	def count_func(funcs, all):
		dist = OrderedDict({key: 0 for key in all})
		total = 0
		for func in funcs:
			dist[func[0]] += int(func[1])
			total += int(func[1])
		for fname in dist:
			dist[fname] /= total
		return dist, total

	dist1, tot1 = count_func(funcs1, allFuncs)
	dist2, tot2 = count_func(funcs2, allFuncs)
	probArr1 = np.array(list(dist1.values()))
	probArr2 = np.array(list(dist2.values()))

	avgProb = 0.5 * (probArr1 + probArr2)
	kl_Divergence1 = stats.entropy(probArr1, avgProb)
	kl_Divergence2 = stats.entropy(probArr2, avgProb)
	js_Divergence = 0.5 * (kl_Divergence1 + kl_Divergence2)

	return js_Divergence

MAX_FREQ = 200
BASE_FREQ = 50
STABLE_RND_TRD = 5
class DynRunner():
	def __init__(self, dur, topn, threshold):
		self.dur = dur
		self.topn = topn
		self.threshold = threshold
		self.nowFreq = BASE_FREQ
		self.stableRndNum = 0
		self.lastRunFuncs = None
		self.lastFreq = self.nowFreq
		
	
	def testSpecjbb(self, rndNum, resDir, targets):
		if(not os.path.exists(resDir)): os.makedirs(resDir)
		testSpecjbb_LOG_PATH = os.path.join(resDir, "log")
		logger = init_logger(testSpecjbb_LOG_PATH, "costFreqLogger")

		for r in range(rndNum):
			targetCount = defaultdict(int)
			logger.info(f"round{r}")
			roundResDir = os.path.join(resDir, f"round={r}")
			if(os.path.exists(roundResDir)): shutil.rmtree(roundResDir)
			os.makedirs(roundResDir)
			pstatResPath = os.path.join(roundResDir, "pidstat")
			tmpPath = os.path.join(roundResDir, "tmp")

			logger.info("start specjbb")
			specPid, specProc = runSpecjbb(roundResDir)
			time.sleep(10)

			logger.info("start pidstat")
			pidStatCmd = f"pidstat -u -p {specPid} {1} > {pstatResPath}"
			pidStatProc = subprocess.Popen(['bash', '-c', pidStatCmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			time.sleep(3)

			while(checkPid(specPid)):
				stopProfJava(specPid)
				logger.info(f"freq = {self.nowFreq}")
				itv = freq2itv(self.nowFreq)

				profilerTrd = runProfJava(specPid, itv, self.dur, tmpPath, False)
				profilerTrd.join()

				thisRunFuncs = readCollapsed(tmpPath, self.topn)
				rndTargetCount = countCollapsed(tmpPath, targets)

				for func in rndTargetCount:
					targetCount[func] += itv*rndTargetCount[func]

				self.lastFreq = self.nowFreq
				self.nowFreq = self.adjFreq(self.lastRunFuncs, thisRunFuncs)
				self.lastRunFuncs = thisRunFuncs

			specProc.wait()
			pidStatProc.wait()
			with open(os.path.join(roundResDir, "targets"), "w") as f:
				for key in targetCount:
					f.write(f"{key}: {targetCount[key]}\n")
		os.remove(tmpPath)
		return

	def adjFreq(self, funcs1, funcs2):
		if(not funcs1 or not funcs2):
			return self.nowFreq
		js_div = calc_Js_Div(funcs1, funcs2)

		if(js_div < self.threshold):
			if(self.stableRndNum < STABLE_RND_TRD):
				freq = self.nowFreq
			else:
				freq = self.nowFreq * 0.8
			self.stableRndNum += 1
		else:
			freq = self.nowFreq * 1.25
			self.stableRndNum = 0
		
		freq = min(freq, MAX_FREQ)
		freq = max(freq, BASE_FREQ)
		return freq