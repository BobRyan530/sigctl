#!/usr/bin/env python
# Bob Ryan 8/6/17

debug = True    # What's the best way to pass a variable like this from user program?

def getIdn(instr):
    return(instr.ask("*IDN?"))

def waveformSetup(instr, args):
    instr.write("WFSU SP,{},NP,{},FP,{},SN,0".format(args.sp, args.np, args.fp))
    if debug:
        print('sent WFSU SP,{},NP,{},FP,{},SN,0'.format(args.sp, args.np, args.fp))
    instr.write("WFSU TYPE,{}".format(args.wtype))
    if debug:
        print('sent WFSU TYPE,{}'.format(args.wtype))

def getVdiv(instr, channel):
    instr.write("{}:VDIV?".format(channel))
    r = instr.read_raw()
    r = r.split(" ")[1][:-2]
    return(float(r))

def getOffset(instr, channel):
    instr.write("{}:OFST?".format(channel))
    r = instr.read_raw()
    r = r.split(" ")[1][:-2]
    return(float(r))

def getStartTime(instr):
    instr.write("TRDL?")
    r = instr.read_raw()  # time value at center of screen
    tvcos = r.split(" ")[1][:-1]
    if 'ns' in tvcos:
        tvcos = tvcos.split('ns')[0]
        tvcos = float(tvcos) / 10**9
    elif 'us' in tvcos:
        tvcos = tvcos.split('us')[0]
        tvcos = float(tvcos) / 10**6
    elif 'ms' in tvcos:
        tvcos = tvcos.split('ms')[0]
        tvcos = float(tvcos) / 10**3
    instr.write("TDIV?")
    r = instr.read_raw()   # timebase
    tdiv = r.split(" ")[1][:-2]
    tdiv = float(tdiv)
    tfirstpoint = tvcos - (tdiv * 14 / 2)
    return(tfirstpoint)

def getTimeInterval(instr):
    instr.write("SARA?")
    r = instr.read_raw()  # time value at center of screen
    srate = r.split(" ")[1][:-1]
    if 'GSa' in srate:
        srate = srate.split('GSa')[0]
        srate = float(srate) * 10**9
    elif 'MSa' in srate:
        srate = srate.split('MSa')[0]
        srate = float(srate) * 10**6
    elif 'KSa' in srate:
        srate = srate.split('KSa')[0]
        srate = float(srate) * 10**3
    elif 'Sa' in srate:
        srate = srate.split('Sa')[0]
        srate = float(srate)
    tint = 1 / srate
    return(float(tint))
  
def recvWaveform(instr, channels):
    vals = []
    for channel in channels:
        if debug:
            print('sending: {}:WF? ALL'.format(channel))
        instr.write("{}:WF? ALL".format(channel))
        vals.append(instr.read_raw())
    return(vals)

def convertNone(value, chindex, vdiv, voffset):
    if value > 127:
        value = value - 255
    return(value * 0.03125)     # this is 4 / 128 (number of grids +/- * max value)

def convertVoltage(value, chindex, vdiv, voffset):
    if value > 127:
        value = value - 255
    voltage = value * (vdiv[chindex] / 25) - voffset[chindex]
    return(voltage)

def convertOutput(value, chindex, vdiv, voffset, cb=convertNone):
	return(cb(value, chindex, vdiv, voffset))
