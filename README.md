# sigctl
Python tools to access Siglent-manufactured oscilloscopes through the VXI11 interface.

Tested on a B&K Precision 2557 which I believe is a rebadged Siglent SDS1204cfl.

Examples:
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

Display all channels on device at 192.168.1.88
		./sigview.py -i 192.168.1.88

Display channel 3 and don't scale to volts
		./sigview.py -i 192.168.1.88 -c ch3 -n
 
Display all points in memory for channels 1 and 2
		./sigview.py -i 192.168.1.88 -c ch2,CH1 --wtype 1
