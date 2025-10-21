import platform


def get_os_info():
	return {
		'system': platform.system(),
		'version': platform.version(),
		'release': platform.release(),
		'architecture': platform.machine()
	}