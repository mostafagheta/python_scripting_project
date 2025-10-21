import psutil


def get_memory_info():
	vm = psutil.virtual_memory()
	return {
		'total': vm.total,
		'available': vm.available,
		'used': vm.used,
		'percent': vm.percent,
		'type': 'Unknown',
		'frequency': 'Unknown'
	}