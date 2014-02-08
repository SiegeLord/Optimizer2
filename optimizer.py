#!/usr/bin/env python

from ConfigParser import SafeConfigParser, NoOptionError
from argparse import ArgumentParser
from subprocess import Popen, PIPE

import fileinput
import shlex
import re

from differential_evolution import DifferentialEvolutionOptimizer

# pop is an array of vectors with the first element being the fitness
# and the remaining elements being the parameters
def runner(cmd_str, res_re, max_launches, pop, verbose):
	idx = 0
	
	while idx < len(pop):
		num_launches = min(len(pop) - idx, max_launches)
		procs = []
		cmds = []
		for i in range(num_launches):
			cmds.append(cmd_str.format(*pop[idx + i][1:]))
			if verbose:
				print 'Running:', cmds[i]
			args = shlex.split(cmds[i])
			procs.append(Popen(args, stdout=PIPE))
		
		for i in range(num_launches):
			if procs[i].wait() != 0:
				raise Exception('\'' + cmds[i] + '\' returned a non-0 status!')
			out, _ = procs[i].communicate()
			if res_re:
				match = res_re.search(out)
				if match:
					l = match.group(1)
				else:
					raise Exception('Could not parse the output!')
			else:
				l = out.splitlines()[-1]
				
			pop[idx + i][0] = float(l)
		idx += num_launches

def main():
	parser = ArgumentParser()
	parser.add_argument('--cfg', dest='cfg_name', help='Configuration file name. If omitted, the file will be read from stdin.')
	
	args = parser.parse_args()
	
	cfg = SafeConfigParser();
	
	if args.cfg_name:
		cfg.read(args.cfg_name)
	else:
		cfg.readfp(fileinput.input())
	
	cmd_str = cfg.get('options', 'command')
	try:
		max_launches = cfg.getint('options', 'max_launches')
	except NoOptionError:
		max_launches = 1000

	try:
		pat = cfg.get('options', 'result_re')
		res_re = re.compile(pat)
	except NoOptionError:
		res_re = None
	
	try:
		num_args = cfg.getint('options', 'num_args')
	except NoOptionError:
		num_args = 1

	limits = []
	for i in range(num_args):
		try:
			lim_str = cfg.get('options', 'limit%d' % i)
			lim = []
			for s in lim_str[1:-1].split():
				lim.append(float(s))
			if len(lim) != 2:
				raise Exception('Invalid limit string "%s" (expected "[low hi]")' % lim_str)
		except NoOptionError:
			lim = [0.0, 1.0]
		limits.append(lim)
	
	alg_str = cfg.get('options', 'algorithm')
	if alg_str == 'de':
		opt = DifferentialEvolutionOptimizer(cfg, limits, lambda pop: runner(cmd_str, res_re, max_launches, pop, False))
		pop = opt.run()
		for ind in pop:
			print ind[0], ind[1:]
	else:
		raise Exception('Unknown algorithm \'' + alg_str + '\'')

if __name__ == '__main__':
    main()
