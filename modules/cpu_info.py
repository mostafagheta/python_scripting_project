import platform
import psutil

try:
	import cpuinfo
except ImportError:
	cpuinfo = None


def get_cpu_info():
	info = {}
	try:
		if cpuinfo:
			ci = cpuinfo.get_cpu_info()
			info = {
				'brand': ci.get('brand_raw'),
				'arch': ci.get('arch'),
				'hz': ci.get('hz_advertised_friendly'),
				'cores': psutil.cpu_count(logical=False),
				'threads': psutil.cpu_count(logical=True),
				'usage': psutil.cpu_percent(interval=0.5)
			}
		else:
			info = {
				'brand': platform.processor(),
				'arch': platform.machine(),
				'cores': psutil.cpu_count(logical=False),
				'threads': psutil.cpu_count(logical=True),
				'usage': psutil.cpu_percent(interval=0.5)
			}
	except Exception as e:
		info['error'] = str(e)
	return info