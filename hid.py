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
	print 'device:', "{:04x}".format(device.idVendor)+":{:04x}".format(device.idProduct)

# Detach linux kernel driver if needed
reattach = False
if device.is_kernel_driver_active(0):
	reattach = True
	device.detach_kernel_driver(0)

# Set default configuration
try:
	device.set_configuration()
except usb.core.USBError as e:
	print "USB Error: set_configuration: ", e.strerror
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
	sys.exit(1)
else:
	print 'outEndpoint:', outEndpoint.bEndpointAddress, outEndpoint.wMaxPacketSize

# Test inEndpoint
if inEndpoint is None:
	print "USB Error: IN endpoint not found"
	sys.exit(1)
else:
	print 'inEndpoint:', inEndpoint.bEndpointAddress, inEndpoint.wMaxPacketSize

# Write a data
try:
	# device.write(outEndpoint.bEndpointAddress, RFID_18K6CSetQuickAccessMode, interface.bInterfaceNumber, 1000)
	device.ctrl_transfer(0x40, 0x03, 0, 0, RFID_18K6CSetQuickAccessMode) == len(RFID_18K6CSetQuickAccessMode)
except usb.core.USBError as e:
	print "USB Error: write(out):", e.strerror
	sys.exit(1)

# Read a data
try:
	data = device.read(inEndpoint.bEndpointAddress, 3, interface.bInterfaceNumber, 1000)
except usb.core.USBError as e:
	print "USB Error: read(in):", e.strerror
	sys.exit(1)

print "Data: ", data

# Release the interface
usb.util.dispose_resources(device)

# Re-attach linux kernel driver if needed
if reattach:
	device.attach_kernel_driver(0)

