import customtkinter as ctk
import threading
import modules.cpu_info as cpu_info
import modules.memory_info as memory_info
import modules.gpu_info as gpu_info
import modules.temp_info as temps
import modules.volt_info as volt_power
import modules.network as network_info
import modules.os_info as os_info
import modules.remote_monitor as remote_monitor
import modules.stress_test as stress_test
import modules.motherboard_info as motherboard_info
import json
import pprint
import tkinter as tk




class App(ctk.CTk):
	def __init__(self):
		super().__init__()
		self.title("Professional System Monitor")
		self.geometry("1200x700")
		ctk.set_appearance_mode("dark")
		ctk.set_default_color_theme("blue")

		# Configure grid for landscape layout
		self.grid_rowconfigure(1, weight=2)
		self.grid_columnconfigure(1, weight=3)

		# Header with catchy shapes
		header = ctk.CTkFrame(self, height=60)
		header.grid(row=0, column=0, columnspan=2, sticky='nsew')
		# decorative shapes (simple colored badges)
		try:
			shape1 = ctk.CTkLabel(header, text='   ', fg_color='#2ecc71', width=24, height=24, corner_radius=12)
			shape1.pack(side='left', padx=(12,6), pady=12)
			shape2 = ctk.CTkLabel(header, text='   ', fg_color='#3498db', width=24, height=24, corner_radius=12)
			shape2.pack(side='left', padx=6, pady=12)
		except Exception:
			pass

		title = ctk.CTkLabel(header, text="Professional System Monitor", font=ctk.CTkFont(size=20, weight="bold"))
		title.pack(side='left', padx=12)
		self.status_label = ctk.CTkLabel(header, text="Ready", anchor='e')
		self.status_label.pack(side='right', padx=20)

		# Left navigation (scrollable)
		self.left_frame = ctk.CTkScrollableFrame(self, width=260, corner_radius=8)
		self.left_frame.grid(row=1, column=0, sticky='nsw', padx=(16,8), pady=12)

		# Main content area
		content_frame = ctk.CTkFrame(self, corner_radius=8)
		content_frame.grid(row=1, column=1, sticky='nsew', padx=(8,16), pady=12)
		content_frame.grid_rowconfigure(0, weight=1)
		content_frame.grid_columnconfigure(0, weight=1)

		# Large output area using tk.Text for colored output
		mono_font = ('Courier New', 14)
		text_frame = ctk.CTkFrame(content_frame)
		text_frame.grid(row=0, column=0, sticky='nsew', padx=12, pady=12)
		text_frame.grid_rowconfigure(0, weight=1)
		text_frame.grid_columnconfigure(0, weight=1)

		self.output = tk.Text(text_frame, wrap='word', font=mono_font, bg='#0f1720', fg='white', padx=8, pady=8)
		self.output.grid(row=0, column=0, sticky='nsew')

		scrollbar = tk.Scrollbar(text_frame, command=self.output.yview)
		scrollbar.grid(row=0, column=1, sticky='ns')
		self.output.config(yscrollcommand=scrollbar.set)

		# Configure tags for colors
		self.output.tag_configure('key', foreground='white')
		self.output.tag_configure('good', foreground='#2ecc71')
		self.output.tag_configure('bad', foreground='#e74c3c')
		self.output.tag_configure('neutral', foreground='#95a5a6')
		self.output.tag_configure('mono', font=mono_font)

		# Buttons list
		buttons = [
			("CPU Info", self.show_cpu_info),
			("Memory Info", self.show_memory_info),
			("GPU Info", self.show_gpu_info),
			("Temperatures", self.show_temps),
			("Voltages & Power", self.show_volt_power),
			("Network Rates", self.show_network_rates),
			("OS Info", self.show_os_info),
			("Motherboard", self.show_motherboard),
			("Stress Test (10s)", lambda: threading.Thread(target=self.run_stress, args=(10,), daemon=True).start()),
			("Remote Monitor", self.show_remote_stub),
		]

		for i, (text, cmd) in enumerate(buttons):
			btn = ctk.CTkButton(self.left_frame, text=text, command=cmd, anchor='w')
			btn.pack(fill='x', pady=6, padx=8)

		# Bottom status bar
		status = ctk.CTkFrame(self, height=28)
		status.grid(row=2, column=0, columnspan=2, sticky='nsew')
		self.footer_label = ctk.CTkLabel(status, text="© System Monitor — Ready", anchor='w')
		self.footer_label.pack(side='left', padx=12)

	def write_output(self, text):
		# Clear
		self.output.configure(state='normal')
		self.output.delete('1.0', 'end')
		# If dict/list, render line by line with colors
		if isinstance(text, dict):
			# Show all keys, including None — use neutral color for missing values
			for k, v in text.items():
				self.output.insert('end', f"{k}: ", ('key',))
				if v is None or (isinstance(v, str) and v.strip() == ''):
					self.output.insert('end', f"{v}\n", ('neutral', 'mono'))
				else:
					if isinstance(v, (dict, list)):
						pretty = pprint.pformat(v, width=120)
						self.output.insert('end', pretty + '\n', ('good', 'mono'))
					else:
						self.output.insert('end', f"{v}\n", ('good', 'mono'))
		elif isinstance(text, list):
			for item in text:
				self.output.insert('end', str(item) + '\n', ('mono',))
		else:
			# try to decode JSON
			try:
				obj = json.loads(text)
				self.write_output(obj)
				return
			except Exception:
				self.output.insert('end', str(text), ('mono',))

		self.output.see('end')
		self.output.configure(state='disabled')

	def show_cpu_info(self):
			self.write_output(cpu_info.get_cpu_info())

	def show_memory_info(self):
			self.write_output(memory_info.get_memory_info())

	def show_gpu_info(self):
			self.write_output(gpu_info.get_gpu_info())

	def show_temps(self):
			self.write_output(temps.get_temperatures())

	def show_volt_power(self):
			v = volt_power.get_voltages()
			p = volt_power.get_power()
			self.write_output({'voltages': v, 'power': p})

	def show_network_rates(self):
			self.write_output({'note': 'Measuring network rates...'})
			threading.Thread(target=lambda: self.write_output(network_info.get_network_rates()), daemon=True).start()

	def show_os_info(self):
			self.write_output(os_info.get_os_info())

	def show_motherboard(self):
		info = motherboard_info.get_motherboard_info()
		# convert to display dict and let write_output filter None values
		if 'note' in info:
			self.write_output({'note': info['note']})
			return
		display = {}
		if info.get('manufacturer'):
			display['Manufacturer'] = info.get('manufacturer')
		if info.get('product'):
			display['Product'] = info.get('product')
		if info.get('bios_version'):
			display['BIOS'] = info.get('bios_version')
		if info.get('chipset'):
			chip = info.get('chipset')
			if len(chip) > 120:
				chip = chip[:115] + '...'
			display['Chipset'] = chip
		self.write_output(display)

	def run_stress(self, seconds=10):
		self.write_output(f"Starting stress test for {seconds}s...\n")
		stress_test.run_stress_test(seconds)
		self.write_output(f"Stress test completed ({seconds}s)")

	def show_remote_stub(self):
			self.write_output(remote_monitor.query_remote('host', 'user'))


if __name__ == '__main__':
	app = App()
	app.mainloop()