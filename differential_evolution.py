# Copyright (c) 2014 by Pavel Sountsov
#
# All rights reserved. Distributed under GPL 3.0. For full terms see the file LICENSE.

from ConfigParser import NoOptionError
import random

# Code adapted from C code by Rainer Storn, available at: http://www.icsi.berkeley.edu/~storn/code.html

class DifferentialEvolutionOptimizer:
	def __init__(self, cfg, limits, runner):
		self.pop_size = cfg.getint('de', 'pop_size')
		if self.pop_size < 5:
			self.pop_size = 5
		self.best_strategy = cfg.get('de', 'strategy') != 'best'
		self.cross = cfg.getfloat('de', 'cross')
		self.max_gen = cfg.getint('de', 'max_gen')
		try:
			self.factor = cfg.getfloat('de', 'factor')
		except NoOptionError:
			self.factor = None
		
		self.init = []
		idx = 0
		while True:
			try:
				init_str = cfg.get('de', 'init%d' % idx)
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
		self.runner = runner
	
	def run(self):
		parents = []
		for init in self.init:
			parents.append([0] + init)
		for _ in range(self.pop_size - len(self.init)):
			ind = [0]
			for lim in self.limits:
				ind.append(lim[0] + random.random() * (lim[1] - lim[0]))
			parents.append(ind)
		
		self.runner(parents)
		parents.sort()
		
		print 'Initial best: ', parents[0][0], parents[0][1:]
		
		for gen in range(self.max_gen):
			factor = self.factor
			if factor == None:
				factor = random.random() * 0.5 + 0.5
			
			children = []
			for ii in range(self.pop_size):
				# Pick 3 other, distinct population members
				while True:
					r1 = random.randrange(self.pop_size)
					if r1 != ii:
						break
				while True:
					r2 = random.randrange(self.pop_size)
					if r2 != ii and r2 != r1:
						break
				while True:
					r3 = random.randrange(self.pop_size)
					if r3 != ii and r3 != r2 and r3 != r1:
						break
				
				child = parents[ii][:]
				j = random.randrange(len(self.limits))
				if self.best_strategy:
					for k in range(len(self.limits)):
						z = (j + k) % len(self.limits) + 1
						child[z] += factor * (parents[0][z] - child[z]) + factor * (parents[r2][z] - parents[r3][z])
						if random.random() > self.cross:
							break
					origin = child
				else:
					for k in range(len(self.limits)):
						z = (j + k) % len(self.limits) + 1
						child[z] = parents[r1][z] + factor * (parents[r2][z] - parents[r3][z])
						if random.random() > self.cross:
							break
					origin = parents[r1]
				
				for k in range(len(self.limits)):
					z = k + 1
					if child[z] < self.limits[k][0]:
						child[z] = self.limits[k][0] + random.random() * (origin[z] - self.limits[k][0])
					
					if child[z] > self.limits[k][1]:
						child[z] = self.limits[k][1] + random.random() * (origin[z] - self.limits[k][1])
				
				children.append(child)
			self.runner(children)
			pop = children + parents
			pop.sort()
			parents = pop[:self.pop_size]
			print 'Generation ', gen + 1, 'best: ', parents[0][0], parents[0][1:]
		return pop
