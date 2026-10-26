#!/usr/bin/env python3

import argparse
import csv
import sys

import vxi11

import sigctl


def convertLogic(voltage, vih):
    return 1 if voltage > vih else 0


def formatRate(srate):
    """sigrok wants a plain number; avoid '1000000.0'."""
    return str(int(round(srate))) if abs(srate - round(srate)) < 1e-6 else repr(srate)


def writeCSV(instr, scope, args):
    n, data = scope.fetch(instr)
    channels = scope.channels
    convcb = sigctl.convertNone if args.noconversion else sigctl.convertVoltage
    with open(args.filename, 'w', newline='') as f:
        f.write(';samplerate={}\n'.format(formatRate(scope.srate)))
        builder = csv.writer(f, delimiter=',')
        if args.sigrok:
            builder.writerow(channels)
        else:
            builder.writerow(['timestamp'] + channels)
        for i in range(n):
            if args.sigrok:
                builder.writerow([convertLogic(sigctl.convertVoltage(data[x][i], x, scope.vdiv, scope.voffset), args.vih)
                                  for x in range(len(channels))])
            else:
                ts = scope.tstart + scope.tint * i
                builder.writerow([ts] + [sigctl.convertOutput(data[x][i], x, scope.vdiv, scope.voffset, convcb)
                                         for x in range(len(channels))])
    return n


def main():
    parser = argparse.ArgumentParser()
    sigctl.addCommonArgs(parser)
    parser.add_argument("-f", "--filename", required=True, help="filename to dump output to")
    parser.add_argument("--sigrok", default=False, action='store_true', help="output csv in a format usable by sigrok")
    parser.add_argument("--vih", default=2.00, type=float, help="voltage level above which is considered logic high")
    args = parser.parse_args()
    sigctl.debug = args.debug

    try:
        instr = vxi11.Instrument(args.ip)
        scope = sigctl.ScopeSetup(instr, args)
        n = writeCSV(instr, scope, args)
    except (OSError, vxi11.vxi11.Vxi11Exception, ValueError) as e:
        sys.exit('error talking to {}: {}'.format(args.ip, e))
    if args.debug:
        print('wrote {} samples x {} channels to {}'.format(n, len(scope.channels), args.filename))


if __name__ == "__main__":
    main()
