
def read_file(path):
	print(f"[loomaa] Reading file: {path}")
	# TODO: Implement file reading

def write_file(path, content):
	print(f"[loomaa] Writing file: {path}")
	with open(path, 'w', encoding='utf-8') as f:
		f.write(content)

def log(msg):
	print(f"[loomaa] {msg}")

def load_config(path):
	print(f"[loomaa] Loading config: {path}")
	# TODO: Implement config loading
