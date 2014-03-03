# Copyright (c) 2014 by Pavel Sountsov
#
# All rights reserved. Distributed under GPL 3.0. For full terms see the file LICENSE.

from ConfigParser import NoOptionError
from subprocess import Popen, PIPE
from optimizer2.common_evolution import *

import random
import time
import shlex

class Cont:
	def __init__(self, cmd_str, res_re, max_launches, verbose):
		self.cmd_str = cmd_str
		self.res_re = res_re
		self.max_launches = max_launches
		self.tasks = []
		self.procs = []
		self.verbose = verbose
		self.cmds = []
		for _ in range(max_launches):
			self.tasks.append(None)
			self.procs.append(None)
			self.cmds.append(None)
	
	def add_task(self, pop_idx, pop_indiv):
		for ii in range(self.max_launches):
			if self.procs[ii] == None:
				self.tasks[ii] = (pop_idx, pop_indiv[:])
				self.cmds[ii] = self.cmd_str.format(*pop_indiv[1:])
				if self.verbose:
					print 'Running:', self.cmds[ii]
				args = shlex.split(self.cmds[ii])
				self.procs[ii] = Popen(args, stdout=PIPE)
				return True
		return False
	
	def poll_task(self):
		for ii in range(self.max_launches):
			if self.procs[ii] != None:
				if self.procs[ii].poll() != None:
					out, _ = self.procs[ii].communicate()
					if self.procs[ii].returncode != 0:
						print out
						raise Exception('\'' + self.cmds[ii] + '\' returned a non-0 status!')
					if self.res_re:
						match = self.res_re.search(out)
						if match:
							l = match.group(1)
						else:
							raise Exception('Could not parse the output!')
					else:
						l = out.splitlines()[-1]
					self.tasks[ii][1][0] = float(l)
					self.procs[ii] = None

					return self.tasks[ii]
		return None

	def kill_all(self):
		for ii in range(self.max_launches):
			if self.procs[ii] != None:
				self.procs[ii].terminate()

class ContDifferentialEvolutionOptimizer:
	def __init__(self, cfg, limits, cmd_str, res_re, max_launches):
		self.runner = Cont(cmd_str, res_re, max_launches, False)
		
		self.pop_size = cfg.getint('cont_de', 'pop_size')
		if self.pop_size < 5:
			self.pop_size = 5
		self.cross = cfg.getfloat('cont_de', 'cross')
		self.max_trials = cfg.getint('cont_de', 'max_trials')
		try:
			self.factor = cfg.getfloat('cont_de', 'factor')
		except NoOptionError:
			self.factor = None
		try:
			self.min_var = cfg.getfloat('cont_de', 'min_var')
		except NoOptionError:
			self.min_var = 0
		
		try:
			self.sleep_dur = cfg.getfloat('cont_de', 'sleep_dur')
		except NoOptionError:
			self.sleep_dur = 1.0
		
		self.init = []
		idx = 0
		while True:
			try:
				init_str = cfg.get('cont_de', 'init%d' % idx)
			except NoOptionError:
				break

			init = []
			for s in init_str[1:-1].split():
				init.append(float(s))
			if len(init) != len(limits):
				raise Exception('Invalid init string "%s" (expected "[param0 param1 ...]")' % init_str)
			self.init.append(init)
			idx += 1
		
		self.limits = limits

	def run(self):
		parents = new_pop(self.init, self.pop_size, self.limits)
		evaluating = []
		for _ in range(self.pop_size):
			evaluating.append(False)
		
		factor = self.factor
		if factor == None:
			factor = random.random() * 0.5 + 0.5
		
		trial = 0
		pop_idx = 0
		children = []
		while trial < self.max_trials:
			while True:
				if self.runner.add_task(pop_idx, mutate(parents, self.limits, factor, self.cross, pop_idx, None)):
					pop_idx = (pop_idx + 1) % self.pop_size
				else:
					break
			
			while True:
				ret = self.runner.poll_task()
				if not ret:
					break
				trial += 1
				idx, indiv = ret
				children.append(indiv)

			if len(children) >= self.pop_size:
				if self.factor == None:
					factor = random.random() * 0.5 + 0.5
				
				pop = children + parents
				pop.sort()
				parents = pop[:self.pop_size]
				var = pop_variance(parents)
				print 'Trial', trial, 'best:', parents[0][1:], 'fit:', parents[0][0], 'parents var:', var
				if var < self.min_var:
					print 'Variance lower than minimum variance (%f). Stopping.' % self.min_var
					break
				children = []
			
			if trial == self.max_trials - 1:
				print 'Maximum number of trials reached. Stopping.'
				break

			time.sleep(self.sleep_dur)
		self.runner.kill_all();
		return pop
