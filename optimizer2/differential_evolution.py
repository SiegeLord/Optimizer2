# Copyright (c) 2014 by Pavel Sountsov
#
# All rights reserved. Distributed under GPL 3.0. For full terms see the file LICENSE.

from ConfigParser import NoOptionError
import random

from optimizer2.array_parser import parse_array
from optimizer2.common_evolution import *

# Code adapted from C code by Rainer Storn, available at: http://www.icsi.berkeley.edu/~storn/code.html

class DifferentialEvolutionOptimizer:
	def __init__(self, cfg, limits, runner):
		self.pop_size = cfg.getint('de', 'pop_size')
		if self.pop_size < 5:
			self.pop_size = 5
		self.best_strategy = cfg.get('de', 'strategy') == 'best'
		self.cross = cfg.getfloat('de', 'cross')
		self.max_gen = cfg.getint('de', 'max_gen')
		try:
			self.factor = cfg.getfloat('de', 'factor')
		except NoOptionError:
			self.factor = None
		try:
			self.min_var = cfg.getfloat('de', 'min_var')
		except NoOptionError:
			self.min_var = 0
		
		self.init = []
		idx = 0
		while True:
			try:
				init_str = cfg.get('de', 'init%d' % idx)
			except NoOptionError:
				break

			init = parse_array(init_str)
			if len(init) != len(limits):
				raise Exception('init%d invalid: expected %d parameters but got %d.' % (idx, len(limits), len(init)))
			self.init.append(init)
			idx += 1
		
		self.limits = limits
		self.runner = runner
	
	def run(self):
		parents = new_pop(self.init, self.pop_size, self.limits)
		
		self.runner(parents)
		parents.sort()
		
		print 'Start best:', parents[0][1:], 'fit:', parents[0][0]
		
		if self.best_strategy:
			best_idx = 0
		else:
			best_idx = None
		
		for gen in range(self.max_gen):
			factor = self.factor
			if factor == None:
				factor = random.random() * 0.5 + 0.5
			
			children = []
			for ii in range(self.pop_size):
				children.append(mutate(parents, self.limits, factor, self.cross, ii, best_idx))
			
			self.runner(children)
			pop = children + parents
			pop.sort()
			parents = pop[:self.pop_size]
			var = pop_variance(parents)
			print 'Gen', gen + 1, 'best:', parents[0][1:], 'fit:', parents[0][0], 'pop var:', var
			if var < self.min_var:
				print 'Variance lower than minimum variance (%f). Stopping.' % self.min_var
				break
			if gen == self.max_gen - 1:
				print 'Maximum generation reached. Stopping.'
		return pop
