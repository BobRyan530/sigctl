#!/usr/bin/env python3
# Bob Ryan 8/6/17
"""Helpers for talking to Siglent oscilloscopes over the VXI-11 interface."""

import argparse
import re
import struct

# Set from the calling program, e.g. ``sigctl.debug = args.debug``.
debug = False

ALL_CHANNELS = ['C1', 'C2', 'C3', 'C4']
HORIZONTAL_DIVS = 14    # horizontal grid divisions on the SDS1000CFL screen
CODES_PER_DIV = 25.0    # ADC codes per vertical division

# Offsets into the LeCroy-style WAVEDESC block Siglent scopes send with WF? ALL
_DESC_COMM_ORDER = 34
_DESC_LENGTHS = 36      # WAVE_DESCRIPTOR, USER_TEXT, RES_DESC1, TRIGTIME, RIS_TIME, RES_ARRAY1, WAVE_ARRAY_1
_LEGACY_DATA_OFFSET = 346 + 20  # what earlier versions hard-coded

_SI_PREFIX = {'': 1.0, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3,
              'k': 1e3, 'g': 1e9}
_NUMBER_RE = re.compile(r'([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*([A-Za-z]*)')


def _log(msg):
    if debug:
        print(msg)


def _toStr(r):
    if isinstance(r, bytes):
        return r.decode('ascii', errors='replace')
    return r


def query(instr, cmd):
    """Send a command and return the response as a stripped string."""
    _log('sending: {}'.format(cmd))
    instr.write(cmd)
    r = _toStr(instr.read_raw()).strip()
    _log('received: {}'.format(r))
    return r


def parseValue(response, unit):
    """Parse a scope reply such as 'C1:VDIV 5.00E-01V', 'TRDL -2.00us' or
    'SARA 1.00GSa/s' into a float in base units."""
    body = response.split(None, 1)[-1]
    m = _NUMBER_RE.search(body)
    if not m:
        raise ValueError('could not parse a number from {!r}'.format(response))
    value = float(m.group(1))
    suffix = m.group(2)
    if suffix.lower().endswith(unit.lower()):
        prefix = suffix[:len(suffix) - len(unit)]
    else:
        prefix = suffix
    if prefix in ('M', 'm'):
        # Siglent replies are often all upper case, so 'MS' on a time value
        # means milliseconds while 'MSa' on a sample rate means mega.
        scale = 1e-3 if unit.lower() == 's' else 1e6
    elif prefix.lower() in _SI_PREFIX:
        scale = _SI_PREFIX[prefix.lower()]
    else:
        raise ValueError('unknown unit {!r} in {!r}'.format(suffix, response))
    return value * scale


def parseChannels(spec):
    """Turn 'all' or a list like 'ch2,C1,3' into ['C1', 'C2', 'C3']."""
    spec = spec.strip().lower()
    if spec in ('', 'all'):
        return list(ALL_CHANNELS)
    channels = set()
    for tok in spec.split(','):
        tok = tok.strip()
        m = re.match(r'^(?:ch|c)?([1-4])$', tok)
        if not m:
            raise argparse.ArgumentTypeError(
                'invalid channel {!r} (use 1-4, C1-C4, CH1-CH4 or all)'.format(tok))
        channels.add('C' + m.group(1))
    return sorted(channels)


def addCommonArgs(parser):
    parser.add_argument("-i", "--ip", required=True, help="ip for vxi11 interface to instrument")
    parser.add_argument("-c", "--channels", default=list(ALL_CHANNELS), type=parseChannels,
                        help="comma separated list of channels to poll (default: all)")
    parser.add_argument("-d", "--debug", default=False, action='store_true', help="increase output verbosity")
    parser.add_argument("-n", "--noconversion", default=False, action='store_true',
                        help="don't scale values to volts. display as currently on oscilloscope")
    parser.add_argument("--fp", default=0, type=int, help="waveform setup: first point")
    parser.add_argument("--sp", default=0, type=int, help="waveform setup: sparsing")
    parser.add_argument("--np", default=0, type=int, help="waveform setup: number of points")
    parser.add_argument("--wtype", default=0, type=int, choices=[0, 1],
                        help="waveform setup: type: 0 = points on screen, 1 = all points in memory")


def getIdn(instr):
    return instr.ask("*IDN?")


def getInstrumentName(idn):
    """'*IDN SIGLENT,SDS1204CFL,SER,FW' -> 'SIGLENT SDS1204CFL'"""
    idn = idn.strip()
    if idn.upper().startswith('*IDN'):
        idn = idn[4:].strip()
    return ' '.join(p.strip() for p in idn.split(',')[0:2])


def waveformSetup(instr, args):
    cmd = "WFSU SP,{},NP,{},FP,{},SN,0".format(args.sp, args.np, args.fp)
    instr.write(cmd)
    _log('sent {}'.format(cmd))
    cmd = "WFSU TYPE,{}".format(args.wtype)
    instr.write(cmd)
    _log('sent {}'.format(cmd))


def getVdiv(instr, channel):
    return parseValue(query(instr, "{}:VDIV?".format(channel)), 'V')


def getOffset(instr, channel):
    return parseValue(query(instr, "{}:OFST?".format(channel)), 'V')


def getTimebase(instr):
    return parseValue(query(instr, "TDIV?"), 's')


def getTriggerDelay(instr):
    """Time value at the center of the screen."""
    return parseValue(query(instr, "TRDL?"), 's')


def getSampleRate(instr):
    return parseValue(query(instr, "SARA?"), 'Sa')


def getStartTime(instr):
    tvcos = getTriggerDelay(instr)
    tdiv = getTimebase(instr)
    return tvcos - (tdiv * HORIZONTAL_DIVS / 2)


def getTimeInterval(instr, sparsing=1):
    """Time between returned points. With sparsing N the scope only sends
    every Nth point, so the interval grows by the same factor."""
    srate = getSampleRate(instr)
    if srate <= 0:
        raise ValueError('scope reported a sample rate of {}'.format(srate))
    return max(1, int(sparsing or 1)) / srate


def recvWaveform(instr, channels):
    vals = []
    for channel in channels:
        _log('sending: {}:WF? ALL'.format(channel))
        instr.write("{}:WF? ALL".format(channel))
        vals.append(instr.read_raw())
    return vals


def extractSamples(raw):
    """Return the raw sample bytes from a 'WF? ALL' response.

    The sample block's location and length are read from the WAVEDESC
    header. If the header can't be found the old fixed offset is used."""
    idx = raw.find(b'WAVEDESC')
    if idx >= 0 and len(raw) >= idx + _DESC_LENGTHS + 28:
        lofirst = struct.unpack_from('<H', raw, idx + _DESC_COMM_ORDER)[0] == 1
        order = '<' if lofirst else '>'
        (desc_len, text_len, _res1, trig_len, ris_len, _res2, n) = \
            struct.unpack_from(order + '7l', raw, idx + _DESC_LENGTHS)
        start = idx + desc_len + text_len + trig_len + ris_len
        if 0 < n and desc_len > 0 and min(text_len, trig_len, ris_len) >= 0 \
                and start + n <= len(raw):
            return raw[start:start + n]
        _log('WAVEDESC looks invalid (len {}, n {}); using fixed offset'.format(desc_len, n))
    else:
        _log('no WAVEDESC found; using fixed offset')
    return raw[_LEGACY_DATA_OFFSET:-2]


def toSigned(value):
    """Scope sends 8-bit two's complement samples."""
    return value - 256 if value > 127 else value


def convertNone(value, chindex, vdiv, voffset):
    """Position in screen divisions, as displayed on the oscilloscope."""
    return toSigned(value) / CODES_PER_DIV


def convertVoltage(value, chindex, vdiv, voffset):
    return toSigned(value) * (vdiv[chindex] / CODES_PER_DIV) - voffset[chindex]


def convertOutput(value, chindex, vdiv, voffset, cb=convertNone):
    return cb(value, chindex, vdiv, voffset)


class ScopeSetup(object):
    """Everything needed to turn raw samples into timestamps and values."""

    def __init__(self, instr, args):
        self.channels = args.channels
        idn = getIdn(instr)
        self.name = getInstrumentName(idn)
        _log('IDN: {}'.format(idn))
        _log('Instrument: {}'.format(self.name))
        _log('Channels: {}'.format(self.channels))

        waveformSetup(instr, args)
        self.vdiv = [getVdiv(instr, c) for c in self.channels]
        self.voffset = [getOffset(instr, c) for c in self.channels]
        self.tstart = getStartTime(instr)
        self.tint = getTimeInterval(instr, args.sp)
        self.srate = 1 / self.tint
        _log('vdiv: {}V\nvoffset: {}V\ntstart: {}s\ntint: {:g}s\nsrate: {}Sa/s\n'.format(
            self.vdiv, self.voffset, self.tstart, self.tint, self.srate))

    def fetch(self, instr):
        """Return (sample_count, [bytes per channel]) for one acquisition."""
        data = [extractSamples(w) for w in recvWaveform(instr, self.channels)]
        n = min(len(d) for d in data) if data else 0
        if any(len(d) != n for d in data):
            _log('channel lengths differ ({}); truncating to {}'.format(
                [len(d) for d in data], n))
        return n, data
