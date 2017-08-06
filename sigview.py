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

def getCSV(channels):
    wf = sigctl.recvWaveform(instr, channels)
    raw = StringIO()
    data = []
    for i in range(0, len(channels)):
        data.append(wf[i][346+skipbytes:-2])
    builder = csv.writer(raw, delimiter=',')
    builder.writerow(['timestamp'] + [x for x in channels])
    idx = 0
    for i in range(0, len(data[0])):
        ts = tstart + (tint * idx)
        builder.writerow([float(ts)] + [float(sigctl.convertOutput(ord(data[x][i]), x, vdiv, voffset, convcb)) for x in range(0, len(channels))])
        idx += 1

    raw.seek(0)
    df = pandas.read_csv(raw)
    raw.close()
    return(df)
  
def animate(i):
    global lasttime, firstrun
    df = getCSV(channels)
    ax1.cla()
    ax1.set_title('{} Waveforms'.format(instrname))
    ax1.set_xlabel('sample time')
    if convcb == sigctl.convertNone:
        ax1.set_ylabel('grid')
        ax1.set_ylim([-4,4])
        firstts = df.iloc[0]['timestamp']
        lastts = df.iloc[len(df.index)-1]['timestamp']
        timespan = lastts - firstts
        tickevery = timespan / 14
        xticks = []
        for i in range(0, 15):
            xticks.append(firstts + (tickevery * i))
        ax1.set_xticks(xticks)
    else:
        ax1.set_ylabel('volts')
    plt.setp(ax1.get_xticklabels(), rotation=30, horizontalalignment='right')
    ax1.grid()
    headers = list(df.columns.values)
    if debug:
        print(headers)
    if 'C1' in headers:
        ax1.plot(df['timestamp'], df['C1'], '-y', label='CH1')
    if 'C2' in headers:
        ax1.plot(df['timestamp'], df['C2'], '-b', label='CH2')
    if 'C3' in headers:
        ax1.plot(df['timestamp'], df['C3'], '-g', label='CH3')
    if 'C4' in headers:
        ax1.plot(df['timestamp'], df['C4'], '-r', label='CH4')
    ax1.legend(bbox_to_anchor=(1.135, 1.17))
    if debug:
        nowtime = time.time()
        print('Frame duration: {} FPS: {}'.format(nowtime - lasttime, 1 / (nowtime - lasttime)))
        lasttime = nowtime

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--ip", required=True, help="ip for vxi11 interface to instrument")
parser.add_argument("-c", "--channels", default='all', help="comma separated list of channels to poll")
parser.add_argument("-d", "--debug", default=False, action='store_true', help="increase output verbosity")
parser.add_argument("-n", "--noconversion", default=False, action='store_true', help="don't scale values to volts. display as currently on oscilloscope")
parser.add_argument("--fp", default=0, help="waveform setup: first point")
parser.add_argument("--sp", default=0, help="waveform setup: sparsing")
parser.add_argument("--np", default=0, help="waveform setup: number of points")
parser.add_argument("--wtype", default=0, choices=['0', '1'], help="waveform setup: type: 0 = points on screen, 1 = all points in memory")
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

    if debug:
        print('vdiv: {}V\nvoffset: {}V\ntstart: {}s\ntint: {:f}s\n'.format(vdiv, voffset, tstart, tint))

    fig = plt.figure()
    ax1 = fig.add_subplot(1,1,1)
    if convcb == sigctl.convertNone:
        ax1.set_ylim([-4,4])
        ax1.set_autoscale_on(False)
    #box = ax1.get_position()
    #ax1.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    lasttime = time.time()

ani = animation.FuncAnimation(fig, animate)#, blit=True)#, interval=100)
plt.show()
