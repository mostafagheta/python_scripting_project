import multiprocessing as mp
import psutil
import time


def _loop(stop):
	x = 0
	while time.time() < stop:
		x += 1


def run_stress_test(duration=10):
	stop = time.time() + duration
	procs = []
	for _ in range(psutil.cpu_count(logical=True)):
		p = mp.Process(target=_loop, args=(stop,))
		p.start()
		procs.append(p)
	for p in procs:
		p.join()