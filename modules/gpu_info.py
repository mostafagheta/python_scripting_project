try:
	import GPUtil
except ImportError:
	GPUtil = None


def get_gpu_info():
	if not GPUtil:
		return {'note': 'GPUtil not installed'}
	gpus = GPUtil.getGPUs()
	return [{'name': g.name, 'mem': g.memoryTotal, 'temp': g.temperature} for g in gpus]


# ────────────────────────────────