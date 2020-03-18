#!/usr/bin/env python3

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

#   Pack the packet
packetSentCount = 0x34971F6D

packedPacketNumber = pack(packetSentCount, 4)
packedFromNode = pack(102, 2)
packedToNode = pack(103, 2)
packedType = pack(1, 1)
packedTotalPackets = pack(25, 1)
packedSubPacketNumber = pack(12, 1)
payload = "Hello node {0}".format(103)

outPacketStart = packedPacketNumber + packedFromNode + packedToNode + packedType 
outPacketEnd = packedTotalPackets + packedSubPacketNumber + payload
outPacketLength = len(outPacketStart + outPacketEnd) + 1
packedPacketLength = pack(outPacketLength, 1)

outPacket = outPacketStart + packedPacketLength + outPacketEnd

print("Packed outPacket = '{0}'".format(outPacket))
print()

#   Unpack the packet
packetNumberIn = unpack(outPacket[0:4])
fromNodeAddressIn = unpack(outPacket[4:6])
toNodeAddressIn = unpack(outPacket[6:8])
typeIn = unpack(outPacket[8:9])
packetLenthIn = unpack(outPacket[9:10])
totalPacketsIn = unpack(outPacket[10:11])
subPacketNumberIn = unpack(outPacket[11:12])
payloadIn = outPacket[12:]

print("Unpacked: packetNumber = {0}, fromNodeAddress = {1}, toNodeAddress = {2}, type = {3}, packetLength = {4}, totalPackets = {5}, \n\tsubPacketIn = {6}, payloadIn = '{7}'".format(hex(packetNumberIn), fromNodeAddressIn, toNodeAddressIn, typeIn, packetLenthIn, totalPacketsIn, subPacketNumberIn, payloadIn))
