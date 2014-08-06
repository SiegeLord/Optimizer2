# Copyright (c) 2014 by Pavel Sountsov
#
# All rights reserved. Distributed under GPL 3.0. For full terms see the file LICENSE.

from ConfigParser import NoOptionError
from subprocess import Popen, PIPE
from optimizer2.common_evolution import *
from optimizer2.array_parser import parse_array
from multiprocessing import Pool, Manager

import random
import time
import shlex

def task_runner(res_queue, cmd_str, res_re, verbose, pop_idx, pop_indiv):
	cmd = cmd_str.format(*pop_indiv[1:])
	if verbose:
		print 'Running:', cmd
	args = shlex.split(cmd)
	proc = Popen(args, stdout=PIPE)
	out, _ = proc.communicate()
	if proc.returncode != 0:
		print out
		raise Exception('\'' + cmd + '\' returned a non-0 status!')
	if res_re:
		match = res_re.search(out)
		if match:
			l = match.group(1)
		else:
			raise Exception('Could not parse the output!')
	else:
		l = out.splitlines()[-1]

	ret = (pop_idx, pop_indiv[:])
	ret[1][0] = float(l)
	res_queue.put(ret)

class Cont:
	def __init__(self, cmd_str, res_re, max_launches, verbose):
		self.cmd_str = cmd_str
		self.res_re = res_re
		self.num_launches = 0
		self.max_launches = max_launches
		self.pool = Pool(max_launches)
		self.manager = Manager()
		self.queue = self.manager.Queue()
		self.verbose = verbose

	def add_task(self, pop_idx, pop_indiv):
		if self.num_launches >= self.max_launches:
			return False
		self.pool.apply_async(task_runner, (self.queue, self.cmd_str, self.res_re, self.verbose, pop_idx, pop_indiv))
		self.num_launches += 1
		return True

	def get_task(self):
		if self.num_launches == 0:
			return None
		res = self.queue.get()
		self.num_launches -= 1
		return res

	def kill_all(self):
		self.pool.terminate()

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

		self.init = []
		idx = 0
		while True:
			try:
				init_str = cfg.get('cont_de', 'init%d' % idx)
			except NoOptionError:
				break

			init = parse_array(init_str)
			if len(init) != len(limits):
				raise Exception('init%d invalid: expected %d parameters but got %d.' % (idx, len(limits), len(init)))
			self.init.append(init)
			idx += 1

		self.limits = limits

	def run(self):
		parents = new_pop(self.init, self.pop_size, self.limits)

		factor = self.factor
		if factor == None:
			factor = random.random() * 0.5 + 0.5

		# First, evaluate the parents
		pop_idx = 0
		num_done = 0
		while num_done < self.pop_size:
			while pop_idx < self.pop_size:
				if self.runner.add_task(pop_idx, parents[pop_idx]):
					pop_idx += 1
				else:
					break

			ret = self.runner.get_task()
			if not ret:
				continue
			idx, indiv = ret
			parents[idx] = indiv
			num_done += 1

		parents.sort()
		var = pop_variance(parents)
		print 'Start best:', parents[0][1:], 'fit:', parents[0][0], 'parents var:', var

		# Now, check the children
		trial = 0
		pop_idx = 0
		children = []
		while True:
			while True:
				if self.runner.add_task(pop_idx, mutate(parents, self.limits, factor, self.cross, pop_idx, None)):
					pop_idx = (pop_idx + 1) % self.pop_size
				else:
					break

			ret = self.runner.get_task()
			if not ret:
				continue
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

			if trial >= self.max_trials - 1:
				print 'Maximum number of trials reached. Stopping.'
				break
		self.runner.kill_all();
		return pop
