import psutil
import time


def get_network_rates(interval=0.5):
	start = psutil.net_io_counters()
	time.sleep(interval)
	end = psutil.net_io_counters()
	recv = (end.bytes_recv - start.bytes_recv) / interval
	sent = (end.bytes_sent - start.bytes_sent) / interval
	return {'recv_bps': recv, 'sent_bps': sent}