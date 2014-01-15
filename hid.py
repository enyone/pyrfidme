# RFID ME reader Python USB HID wrapper

import sys
import usb.core
import usb.util

# RFID ME commands
RFID_18K6CSetQuickAccessMode = "\x5B\x03\x01"
RFID_AntennaPortSetPowerLevel = "\xC0\x03\x12"
RFID_18K6CTagInventory = "\x31\x03\x01"
RFID_18K6CTagRead = "\x37\x09\x01\x02\x00\x00\x00\x00\x06"

# Send USB ctrl_transfer and read response data from IN endpoint
def sendCommand(device, inEndpoint, data):
	
	# Write a data
	try:
		assert device.ctrl_transfer(0x21, 0x09, 0, 0, data) is len(data)
	except usb.core.USBError as e:
		print "USB Error: write(out):", e.strerror
		raise Exception("USB Error", e)
	except AssertionError:
		print "USB Error: write(out): Write error"
		raise Exception("USB Error", e)

	# Read a data
	data = []
	tryouts = 5
	readed = False
	print "Sending command..."

	while 1:
	    try:
		data += device.read(inEndpoint.bEndpointAddress, inEndpoint.wMaxPacketSize)
		if not readed: 
			print "Got response..."
		readed = True
		return data

	    except usb.core.USBError as e:
		tryouts -= 1
		if e.args == ('Operation timed out',) and readed:
			return data
		if tryouts < 0:
			print "USB Error: write(out):", e.strerror
			raise Exception("USB Error", e)


# Check arguments
if len(sys.argv) < 2:
	print "Usage: python hid.py read"
	sys.exit(1)

# Get a device interface (RFID ME reader 1325:c029)
device = usb.core.find(idVendor=0x1325, idProduct=0xc029)

# Test the device is connected and found
if device is None:
	print "Error: Device not found"
	sys.exit(1)
else:
	print 'device:', "0x{:04x}".format(device.idVendor)+":0x{:04x}".format(device.idProduct)

# Detach linux kernel driver if needed
attached = False
try:
	if device.is_kernel_driver_active(0):
		attached = True
		device.detach_kernel_driver(0)
except usb.core.USBError as e:
	print "USB Error: kernel_driver:", e.strerror
	sys.exit(1)

# Set default configuration
claimed = False
try:
	device.set_configuration()
	device.reset()
	usb.util.claim_interface(device, 0)
	claimed = True
except usb.core.USBError as e:
	print "USB Error: set_configuration:", e.strerror
	usb.util.release_interface(device, 0)
	sys.exit(1)

# Get USB configs
config = device.get_active_configuration()
interfaceNumber = config[(0,0)].bInterfaceNumber
alternateSetting = usb.control.get_interface(device, interfaceNumber)

# Get USB interface
interface = usb.util.find_descriptor(
	config, bInterfaceNumber = interfaceNumber,
	bAlternateSetting = alternateSetting
)

print 'interface:', "0x{:04x}".format(interface.bInterfaceNumber)

try:
	# Get IN endpoint
	inEndpoint = usb.util.find_descriptor(
		interface,
		# Match the first IN endpoint
		custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
	)

	# Test inEndpoint
	if inEndpoint is None:
		print "USB Error: IN endpoint not found"
		raise Exception("USB Error", e)
	else:
		print 'inEndpoint:', "0x{:04x}".format(inEndpoint.bEndpointAddress), "max size:", inEndpoint.wMaxPacketSize

	# Set power
	data = sendCommand(device, inEndpoint, RFID_AntennaPortSetPowerLevel)

	print "Response data:", map(hex, data)

	if data[0] == 0xC1 and data[1] == 0x03 and data[2] == 0x0:
		print "RFID_AntennaPortSetPowerLevel: OK"
	else:
		print "RFID_AntennaPortSetPowerLevel: Failed"

	if sys.argv[1] == "read":
		# Tag inventory
		data = sendCommand(device, inEndpoint, RFID_18K6CTagInventory)

		print "Response data:", map(hex, data)

		if data[0] == 0x32 and data[1] == 0x40 and data[2] == 0x0:
			print "RFID_18K6CTagInventory: OK"
			print "Tags found:", data[3]
			print "First tag data:", map(hex, data[5:data[4]+1])
		else:
			print "RFID_18K6CTagInventory: Failed"


except Exception as e:
	print "Error:", e

# Release if claimed
if claimed:
	usb.util.release_interface(device, interface)

# Release the interface
usb.util.dispose_resources(device)

# Re-attach linux kernel driver if needed
if attached:
	device.attach_kernel_driver(0)

