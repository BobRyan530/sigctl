#!/usr/bin/env python

import sigctl
import argparse
import csv
import time
import pandas
import vxi11
from cStringIO import StringIO
from matplotlib import pyplot as plt
import matplotlib.animation as animation

skipbytes = 20  # Some noise in the first ~20 bytes screws up the scaling

def convertLogic(voltage):
    if voltage > args.vih:
        return(1)
    else:
        return(0)

def writeCSV(channels, filename):
    wf = sigctl.recvWaveform(instr, channels)
    raw = StringIO()
    data = []
    for i in range(0, len(channels)):
        data.append(wf[i][346+skipbytes:-2])
    with open(filename, 'wb') as f:
        f.write(';samplerate={}\n'.format(srate))
        builder = csv.writer(f, delimiter=',')
        if args.sigrok:
            builder.writerow([x for x in channels])
        else:
            builder.writerow(['timestamp'] + [x for x in channels])
        idx = 0
        for i in range(0, len(data[0])):
            ts = tstart + (tint * idx)
            if args.sigrok:
                builder.writerow([convertLogic(float(sigctl.convertOutput(ord(data[x][i]), x, vdiv, voffset, sigctl.convertVoltage))) for x in range(0, len(channels))])
            else:
                builder.writerow([float(ts)] + [float(sigctl.convertOutput(ord(data[x][i]), x, vdiv, voffset, convcb)) for x in range(0, len(channels))])
            idx += 1
  
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--ip", required=True, help="ip for vxi11 interface to instrument")
parser.add_argument("-f", "--filename", required=True, help="ip for vxi11 interface to instrument")
parser.add_argument("-c", "--channels", default='all', help="comma separated list of channels to poll")
parser.add_argument("-d", "--debug", default=False, action='store_true', help="increase output verbosity")
parser.add_argument("-n", "--noconversion", default=False, action='store_true', help="don't scale values to volts. display as currently on oscilloscope")
parser.add_argument("--fp", default=0, help="waveform setup: first point")
parser.add_argument("--sp", default=0, help="waveform setup: sparsing")
parser.add_argument("--np", default=0, help="waveform setup: number of points")
parser.add_argument("--wtype", default=0, choices=['0', '1'], help="waveform setup: type: 0 = points on screen, 1 = all points in memory")
parser.add_argument("--sigrok", default=False, action='store_true', help="output csv in a format usable by sigrok")
parser.add_argument("--vih", default=2.00, help="voltage level above which is considered logic high")
args = parser.parse_args()

channels = []

if 'all' in args.channels:
    channels = ['C1', 'C2', 'C3', 'C4']
else:
    if '1' in args.channels:
        channels.append('C1')
    if '2' in args.channels:
        channels.append('C2')
    if '3' in args.channels:
        channels.append('C3')
    if '4' in args.channels:
        channels.append('C4')

if args.noconversion:
    convcb = sigctl.convertNone
else:
    convcb = sigctl.convertVoltage

if args.debug:
    debug = True
else:
    debug = False

if __name__ == "__main__":
    instr =  vxi11.Instrument(args.ip)

    instrname = ' '.join(sigctl.getIdn(instr).split()[1].split(',')[0:2])
    if debug:
        print('IDN: {}'.format(sigctl.getIdn(instr)))
        print('Instrument: {}'.format(instrname))
        print('Channels: {}'.format(channels))

    sigctl.waveformSetup(instr, args)

    vdiv = []
    voffset = []
    for i in range(0, len(channels)):
        vdiv.append(sigctl.getVdiv(instr, channels[i]))
        voffset.append(sigctl.getOffset(instr, channels[i]))
    tstart = sigctl.getStartTime(instr)
    tint = sigctl.getTimeInterval(instr)
    srate = 1 / tint

    if debug:
        print('vdiv: {}V\nvoffset: {}V\ntstart: {}s\ntint: {:f}s\nsrate: {}Sa/s\n'.format(vdiv, voffset, tstart, tint, srate))

    writeCSV(channels, args.filename)
