import binascii
import serial
import threading
import time
import paho.mqtt.client as mqtt
import json
from bitarray import bitarray

mqttBroker = "192.168.1.100"
deviceName = "Inverter"
usbDevice = "/dev/ttyUSB0"

client = mqtt.Client(deviceName)
client.connect(mqttBroker)
serial = serial.Serial(usbDevice, 2400, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=0)

Inverter_Stats_Object = {}

#put your mqtt,post,blahblah here
def handleString(dataName, data):
    Inverter_Stats_Object[dataName] = data


def handle_acFrame(frameBytes):
    # AC main voltage
    data = int.from_bytes(frameBytes[5:7], 'little') * 0.01
    handleString("AC_Main_Voltage", data)

    # AC main current
    data = int.from_bytes(frameBytes[7:9], 'little') * 0.01
    handleString("AC_Main_Current", data)

    # AC inverter voltage
    data = int.from_bytes(frameBytes[9:11], 'little') * 0.01
    handleString("AC_Inverter_Voltage", data)

    # AC inverter current
    data = int.from_bytes(frameBytes[11:13], 'little') * 0.01
    handleString("AC_Inverter_Current", data)

def handle_dcFrame(frameBytes):
    # DC voltage
    data = int.from_bytes(frameBytes[5:7], 'little') * 0.01
    handleString("DC_Voltage", data)

    # DC charge current
    data = int.from_bytes(frameBytes[7:10], 'little') * 0.01
    handleString("DC_Current_Used", data)

    # DC drain current
    data = int.from_bytes(frameBytes[10:13], 'little') * 0.01
    handleString("DC_Current_Provided", data)

def handle_ledFrame(frameBytes):
    ba = bitarray(endian='little')
    ba.frombytes(frameBytes[1:2])
    handleString("LED_Mains", int(ba[0]))
    handleString("LED_Absorption", int(ba[1]))
    handleString("LED_Bulk", int(ba[2]))
    handleString("LED_Float", int(ba[3]))
    handleString("LED_Inverter", int(ba[4]))
    handleString("LED_Overload", int(ba[5]))
    handleString("LED_Low_Battery", int(ba[6]))
    handleString("LED_Temp", int(ba[7]))


def read_from_port(ser):
    while True:
        try:
            byteV = b'\x00'
            length = 0
            frameType = 0x00
            # find start of a frame
            while byteV.hex() != 'ff' and byteV.hex() != '20':
                if ser.inWaiting():
                    length = byteV
                    byteV = ser.read(1)
                else:
                    time.sleep(0.01)
            if byteV.hex() == 'ff':
                frameType = 'ff'
            else:
                frameType = '20'
            byteL = []
            while len(byteL) < int.from_bytes(length, 'little'):
                while ser.inWaiting() == 0:
                    time.sleep(0.01)
                b = ser.read(1)
                byteL.append(b)
            frameBytes = bytes.fromhex(''.join(x.hex() for x in byteL))
            if frameType == '20':
                if byteL[4].hex() == '08':
                    handle_acFrame(frameBytes)
                if byteL[4].hex() == '0c':
                    handle_dcFrame(frameBytes)
            else:
                if byteL[0].hex() == '4c':
                    handle_ledFrame(frameBytes)
        except:
            pass

def write_cmd(ser):
    while True:
        #dc
        serial.write(bytes.fromhex('03ff4600b8'))
        time.sleep(1)
        #ac
        serial.write(bytes.fromhex('03ff4601b7'))
        time.sleep(1)
        #led
        serial.write(bytes.fromhex('02ff4cb3'))
        time.sleep(1)
        try:
            client.publish(deviceName + "/data", json.dumps(Inverter_Stats_Object))
        except:
            print("Error sending data to MQTT.")


thread = threading.Thread(target=read_from_port, args=(serial,))
thread.start()
thread2 = threading.Thread(target=write_cmd, args=(serial,))
thread2.start()