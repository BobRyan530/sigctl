# sigctl
Python tools to access Siglent-manufactured oscilloscopes through the VXI11 interface.

Tested on a B&K Precision 2557 which I believe is a rebadged Siglent SDS1204cfl.

Examples:
```
./sigview.py --help
usage: sigview.py [-h] -i IP [-c CHANNELS] [-d] [-n] [--fp FP] [--sp SP]
				  [--np NP] [--wtype {0,1}]

optional arguments:
  -h, --help            show this help message and exit
  -i IP, --ip IP        ip for vxi11 interface to instrument
  -c CHANNELS, --channels CHANNELS
						comma separated list of channels to poll
  -d, --debug           increase output verbosity
  -n, --noconversion    don't scale values to volts. display as currently on
						oscilloscope
  --fp FP               waveform setup: first point
  --sp SP               waveform setup: sparsing
  --np NP               waveform setup: number of points
  --wtype {0,1}         waveform setup: type: 0 = points on screen, 1 = all
						points in memory
```

```
./sigdump.py --help
usage: sigdump.py [-h] -i IP -f FILENAME [-c CHANNELS] [-d] [-n] [--fp FP]
                  [--sp SP] [--np NP] [--wtype {0,1}] [--sigrok] [--vih VIH]

optional arguments:
  -h, --help            show this help message and exit
  -i IP, --ip IP        ip for vxi11 interface to instrument
  -f FILENAME, --filename FILENAME
                        ip for vxi11 interface to instrument
  -c CHANNELS, --channels CHANNELS
                        comma separated list of channels to poll
  -d, --debug           increase output verbosity
  -n, --noconversion    don't scale values to volts. display as currently on
                        oscilloscope
  --fp FP               waveform setup: first point
  --sp SP               waveform setup: sparsing
  --np NP               waveform setup: number of points
  --wtype {0,1}         waveform setup: type: 0 = points on screen, 1 = all
                        points in memory
  --sigrok              output csv in a format usable by sigrok
  --vih VIH             voltage level above which is considered logic high
```

Display all channels on device at 192.168.1.88
```
./sigview.py -i 192.168.1.88
```

Display channel 3 and don't scale to volts
```
./sigview.py -i 192.168.1.88 -c ch3 -n
```
 
Display all points in memory for channels 1 and 2
```
./sigview.py -i 192.168.1.88 -c ch2,CH1 --wtype 1
```

Dump all channels in csv format to /tmp/wf.csv
```
./sigdump.py -i 192.168.1.88 -f /tmp/wf.csv
```

Dump all channels in csv format which can be imported by sigrok. Vih = +2.1v
```
./sigdump.py -i 192.168.1.88 -f /tmp/wf.csv --sigrok --vih 2.1
```

The above file can be imported into pulseview but will not have timestamps. It can be converted with
```
sigrok-cli -I csv:header=true:samplerate=`grep samplerate /tmp/wf.csv|cut -d= -f2` -i /tmp/wf.csv -o /tmp/wf.sr
```
and the .sr file can be opened by pulseview
