#!/usr/bin/env python

# This file is released into public domain.

from argparse import ArgumentParser
import time


parser = ArgumentParser()
parser.add_argument('--x', dest='x', type=float, required=True)
parser.add_argument('--y', dest='y', type=float, required=True)
parser.add_argument('--wait', dest='wait', default=0.0, type=float)

args = parser.parse_args()

time.sleep(args.wait)

print args.x, args.y, args.wait
x = args.x
y = args.y
print 'Result:', 100.0*((y-x*x)**2.0) + (1-x)**2.0
