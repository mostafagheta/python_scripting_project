import psutil


def get_temperatures():
	try:
		return psutil.sensors_temperatures()
	except Exception:
		return {'note': 'Temperature sensors not supported'}