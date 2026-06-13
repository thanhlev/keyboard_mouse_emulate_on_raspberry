#!/usr/bin/python3

import sys
import dbus
import dbus.mainloop.glib
from logging import error


class MouseClient():
	def __init__(self):
		self.state = [0, 0, 0, 0]
		self.bus = dbus.SystemBus()
		self.btkservice = self.bus.get_object(
			'org.thanhle.btkbservice', '/org/thanhle/btkbservice')
		self.iface = dbus.Interface(self.btkservice, 'org.thanhle.btkbservice')

	def send_current(self):
		try:
			self.iface.send_mouse(0, bytes(self.state))
		except OSError as err:
			error(err)

if __name__ == "__main__":

	if (len(sys.argv) < 5):
		print("Usage: mouse_emulate [button_num dx dy dz]")
		exit()
	client = MouseClient()
	client.state[0] = int(sys.argv[1])
	client.state[1] = int(sys.argv[2])
	client.state[2] = int(sys.argv[3])
	client.state[3] = int(sys.argv[4])
	print("state:", client.state)
	client.send_current()

