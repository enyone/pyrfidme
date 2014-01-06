# RFID ME reader Python USB HID wrapper

import sys
import usb.core
import usb.util

# RFID ME commands
RFID_18K6CSetQuickAccessMode = "\x5B\x03\x01"
RFID_18K6CTagRead = "\x37\x09\x02\x00\x00\x00\x00\x00"

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
	# Get OUT endpoint
	outEndpoint = usb.util.find_descriptor(
		interface,
		# Match the first OUT endpoint
		custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
	)

	# Get IN endpoint
	inEndpoint = usb.util.find_descriptor(
		interface,
		# Match the first IN endpoint
		custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
	)

	# Test outEndpoint
	if outEndpoint is None:
		print "USB Error: OUT endpoint not found"
		raise Exception("USB Error", e)
	else:
		print 'outEndpoint:', "0x{:04x}".format(outEndpoint.bEndpointAddress), "max size:", outEndpoint.wMaxPacketSize

	# Test inEndpoint
	if inEndpoint is None:
		print "USB Error: IN endpoint not found"
		raise Exception("USB Error", e)
	else:
		print 'inEndpoint:', "0x{:04x}".format(inEndpoint.bEndpointAddress), "max size:", inEndpoint.wMaxPacketSize

	# Write a data
	try:
		assert device.ctrl_transfer(0x21, 0x09, 0, 0, RFID_18K6CSetQuickAccessMode) is len(RFID_18K6CSetQuickAccessMode)
		assert device.ctrl_transfer(0x21, 0x09, 0, 0, RFID_18K6CTagRead) is len(RFID_18K6CTagRead)
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
	print "Reading a tag..."

	while 1:
	    try:
		data += device.read(inEndpoint.bEndpointAddress, inEndpoint.wMaxPacketSize)
		if not readed: 
			print "Tag found..."
		readed = True

	    except usb.core.USBError as e:
		tryouts -= 1
		if e.args == ('Operation timed out',) and readed:
			break
		if tryouts < 0:
			print "USB Error: write(out):", e.strerror
			raise Exception("USB Error", e)

except Exception as e:
	print "Error:", e

print "Data:", data

if claimed:
	usb.util.release_interface(device, interface)

# Release the interface
usb.util.dispose_resources(device)

# Re-attach linux kernel driver if needed
if attached:
	device.attach_kernel_driver(0)

