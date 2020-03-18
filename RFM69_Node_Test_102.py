import board
import busio
from time import sleep, time
from math import atan, atan2, cos, pi, sin
from digitalio import DigitalInOut, Direction, Pull

DEBUG = True

PIN_ONBOARD_LED = board.D13
PIN_PACKET_RECEIVED_LED = board.D2
PIN_PACKET_SENT_LED = board.D5

SEND_PACKET_INTERVAL_MIN = 0.5

SPI_SCK = board.SCK
SPI_MISO = board.MISO
SPI_MOSI = board.MOSI

RFM69_CS = DigitalInOut(board.D10)
RFM69_RST = DigitalInOut(board.D11)

RFM69_NETWORK_NODE = 102
RFM69_SEND_TO_NODE = 103

RFM69_SEND_TIMEOUT_SEC = 5.0
RFM69_RECEIVE_TIMEOUT_SEC = 5.0

#   Frequency of the radio in Mhz. Must match your
#       module! Can be a value like 915.0, 433.0, etc.
RFM69_RADIO_FREQ_MHZ = 915.0

import adafruit_rfm69

def millis():
	return time() * 1000

def minutes(start, decimal=0):
	#   60 seconds * 1000 ms = 1 minute
	return round((millis() - start) / 60000, decimal)

def blinkLED(led, wait=0.2, cycles=1):
	for cy in range(cycles):
		led.value = True
		sleep(wait)
		led.value = False
		sleep(wait)

def pack(number, length=4):
	n = number
	g = []

	while n > 0:
		g.append(n & 0xFF)
		n = n >> 8

	t = ""

	for index in range(len(g)):
		t = chr(g[index]) + t

	while len(t) < length:
		t = chr(0) + t

	return t

def unpack(st):
	n = 0
	index = 0
	l = len(st)

	while index < len(st):
	#for index in range(len(st)):
		#sh = 8 * (len(st) - index - 1)
		sh = 8 * (l - index - 1)
		s = st[index]
		o = ord(s)
		n = n + (o << sh)
		index += 1

	return n

#   Initialize the onboard LED
heartBeatLED = DigitalInOut(PIN_ONBOARD_LED)
heartBeatLED.direction = Direction.OUTPUT

packetReceivedLED = DigitalInOut(PIN_PACKET_RECEIVED_LED)
packetReceivedLED.direction = Direction.OUTPUT

packetSentLED = DigitalInOut(PIN_PACKET_SENT_LED)
packetSentLED.direction = Direction.OUTPUT

#   Initialize the I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

#   Initialize the SPI bus
spi = busio.SPI(SPI_SCK, MOSI=SPI_MOSI, MISO=SPI_MISO)

print()
print("This is node #{0}".format(RFM69_NETWORK_NODE))
print()

#   Initialze RFM69 radio
print("Initializing the RFM69 radio")
rfm69 = adafruit_rfm69.RFM69(spi, RFM69_CS, RFM69_RST, RFM69_RADIO_FREQ_MHZ)

# Optionally set an encryption key (16 byte AES key). MUST match both
# on the transmitter and receiver (or be set to None to disable/the default).
rfm69.encryption_key = b'\x01\x02\x03\x04\x05\x06\x07\x08\x01\x02\x03\x04\x05\x06\x07\x08'

rfm69Celsius = rfm69.temperature
rfm69Fahrenheit = round(rfm69Celsius * 1.8 + 32, 1)

#   Print out some RFM69 chip state:
print("RFM69 Radio Data")
print('    Temperature:         {0}°F ({1}°C)'.format(rfm69Fahrenheit, rfm69Celsius))
print('    Frequency:           {0} MHz'.format(round(rfm69.frequency_mhz, 0)))
print('    Bit rate:            {0} kbit/s'.format(rfm69.bitrate / 1000))
print('    Frequency deviation: {0} kHz'.format(rfm69.frequency_deviation / 1000))

loopCount = 0
receivedPacket = False
packetReceivedCount = 0
packetSentCount = 0
resendPacket = False
ackPacketsReceived = 0
acknowledged = False
firstRun = True
startSendMillis = millis()

print()

while True:
	blinkLED(heartBeatLED)
	loopCount += 1

	if DEBUG:
		print("Loop #{0:6d}".format(loopCount))
		print()

	currentSendMinutes = minutes(startSendMillis, 1)

	#
	#   RFM69 radio stuff
	#

	if acknowledged or firstRun or currentSendMinutes >= SEND_PACKET_INTERVAL_MIN:
		packetSentLED.value = True
		sleep(0.5)
		startSendMillis = millis()

		if not resendPacket:
			#   Pack the packet
			packetSentCount += 1
			
			packedPacketNumber = pack(packetSentCount, 4)
			packedFromNode = pack(RFM69_NETWORK_NODE, 2)
			packedToNode = pack(RFM69_SEND_TO_NODE, 2)
			packedType = pack(1, 1)
			packedTotalPackets = pack(25, 1)
			packedSubPacketNumber = pack(12, 1)
			payload = "Hello node {0}".format(RFM69_SEND_TO_NODE)

			outPacketStart = packedPacketNumber + packedFromNode + packedToNode + packedType
			outPacketEnd = packedTotalPackets + packedSubPacketNumber + payload
			outPacketLength = len(outPacketStart + outPacketEnd) + 1
			packedPacketLength = pack(outPacketLength, 1)

			outPacket = outPacketStart + packedPacketLength + outPacketEnd
	   
		print("Sending packet #{0}, '{1}' message!".format(packetSentCount, payload))
		print()

		try:
			rfm69.send(bytes(outPacket, "utf-8", RFM69_SEND_TIMEOUT_SEC))
		except RuntimeError:
			pass

	print('Waiting for packets...')

	inPacket = rfm69.receive(timeout=RFM69_RECEIVE_TIMEOUT_SEC)

	if inPacket is None:
		#   Packet has not been received
		resendPacket = True
		receivedPacket = False
		packetReceivedLED.value = False
		print('Received nothing!')
		print()
		sleep(0.5)
	else:
		#   Received a new packet!
		receivedPacket = True
		packetReceivedCount += 1
		packetReceivedLED.value = True

		#   Start unpacking the packet
		packetNumberIn = unpack(inPacket[0:4])
		fromNodeAddressIn = unpack(inPacket[4:6])
		toNodeAddressIn = unpack(inPacket[6:8])
		typeIn = unpack(outPacket[8:9])
		
		if typeIn == 1:
			#   Standard Packet
			payloadIn = inPacket[12:]
		elif typeIn == 2:
			#   Acknowledgement Packet
			payloadIn = inPacket[10:]
		else:
			print("Invalid Packet: Type {0}".format(typeIn))

		payloadInText = str(payloadIn, 'ASCII')
		
		if typeIn == 2 and payloadInText == "ACK":
			#   ACK packet
			acknowledged = True
			print("Received ACK of packet {0} from node {1}".format(packetNumberIn, fromNodeAddressIn))
		else:
			#   New packet

			print()
			print("Received new type {0} packet {1} from node {2}, raw bytes '{3}'".format(typeIn, packetNumberIn, fromNodeAddressIn, inPacket))

			#
			#   Add packet validation here
			#

			#   Finish unpacking the packet
			if typeIn == 1:
				packetLenthIn = unpack(inPacket[9:10])
				totalPacketsIn = unpack(inPacket[10:11])
				subPacketNumberIn = unpack(inPacket[11:12])

			print("Received payload (ASCII): '{0}'".format(payloadInText))

			sleep(0.2)
			packetReceivedLED.value = False

			if typeIn != 2:
				#   ACK the packet
				packetSentLED.value = True
				sleep(0.5)
				ackPacket = pack(packetNumberIn, 4) + pack(RFM69_NETWORK_NODE, 2) + pack(fromNodeAddress, 2) + pack(RFM69_SEND_TO_NODE, 2) + pack(2, 1)
				ackPacketLength =  len(ackPacket) + 4
				ackPacket = ackPacket + pack(ackPacketLength, 1) + "ACK"

				print("Sending ACK of packet {0} to node {1}".format(packetNumberIn, fromNodeAddressIn))

				try:
					rfm69.send(bytes(ackPacket, "utf-8", RFM69_SEND_TIMEOUT_SEC))
				except RuntimeError:
					pass
		
				packetSentLED.value = False

	firstRun = False
	sleep(0.2)
