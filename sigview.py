#!/usr/bin/env python3

import argparse
import sys
import time

import numpy as np
import vxi11
from matplotlib import pyplot as plt
import matplotlib.animation as animation

import sigctl

COLORS = {'C1': '-y', 'C2': '-b', 'C3': '-g', 'C4': '-r'}


def getTraces(instr, scope, noconversion):
    """Return (timestamps, {channel: values}) as numpy arrays."""
    n, data = scope.fetch(instr)
    ts = scope.tstart + scope.tint * np.arange(n)
    traces = {}
    for x, channel in enumerate(scope.channels):
        codes = np.frombuffer(data[x][:n], dtype=np.int8).astype(float)
        if noconversion:
            traces[channel] = codes / sigctl.CODES_PER_DIV
        else:
            traces[channel] = codes * (scope.vdiv[x] / sigctl.CODES_PER_DIV) - scope.voffset[x]
    return ts, traces


def main():
    parser = argparse.ArgumentParser()
    sigctl.addCommonArgs(parser)
    args = parser.parse_args()
    sigctl.debug = args.debug

    try:
        instr = vxi11.Instrument(args.ip)
        scope = sigctl.ScopeSetup(instr, args)
    except (OSError, vxi11.vxi11.Vxi11Exception, ValueError) as e:
        sys.exit('error talking to {}: {}'.format(args.ip, e))

    fig = plt.figure()
    ax1 = fig.add_subplot(1, 1, 1)
    state = {'lasttime': time.time()}

    def animate(frame):
        ts, traces = getTraces(instr, scope, args.noconversion)
        ax1.cla()
        ax1.set_title('{} Waveforms'.format(scope.name))
        ax1.set_xlabel('sample time (s)')
        if args.noconversion:
            ax1.set_ylabel('grid')
            ax1.set_ylim([-4, 4])
            if len(ts) > 1:
                ax1.set_xticks(np.linspace(ts[0], ts[-1], sigctl.HORIZONTAL_DIVS + 1))
        else:
            ax1.set_ylabel('volts')
        plt.setp(ax1.get_xticklabels(), rotation=30, horizontalalignment='right')
        ax1.grid()
        for channel, values in traces.items():
            ax1.plot(ts, values, COLORS[channel], label='CH' + channel[1])
        ax1.legend(bbox_to_anchor=(1.135, 1.17))
        if args.debug:
            nowtime = time.time()
            dt = nowtime - state['lasttime']
            print('Frame duration: {:.3f}s FPS: {:.1f}'.format(dt, 1 / dt if dt else 0))
            state['lasttime'] = nowtime

    # keep a reference so the animation isn't garbage collected
    ani = animation.FuncAnimation(fig, animate, cache_frame_data=False)  # noqa: F841
    plt.show()


if __name__ == "__main__":
    main()
