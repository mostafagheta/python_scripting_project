def query_remote(host, user, ip=None):
	note = f'Remote monitoring placeholder for {host} as {user}'
	if ip:
		note += f' (IP: {ip})'
	return {'note': note}