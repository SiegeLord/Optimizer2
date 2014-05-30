# Copyright (c) 2014 by Pavel Sountsov
#
# All rights reserved. Distributed under GPL 3.0. For full terms see the file LICENSE.

import random

def pop_variance(pop):
	mean_var = 1
	for z in range(1, len(pop[0])):
		mean = 0.0
		for i in range(len(pop)):
			mean += pop[i][z]
		mean /= len(pop)
		var = 0.0
		for i in range(len(pop)):
			var += (pop[i][z] - mean)**2
		var /= len(pop) - 1
		
		mean_var *= var
	pow(mean_var, 1.0 / (len(pop[0]) - 1))
	return mean_var

def new_pop(init, pop_size, limits):
	parents = []
	for v in init:
		parents.append([float('inf')] + v)
	for _ in range(pop_size - len(init)):
		ind = [float('inf')]
		for lim in limits:
			ind.append(lim[0] + random.random() * (lim[1] - lim[0]))
		parents.append(ind)
	return parents

def mutate(parents, limits, factor, cross, idx, best_idx):
	# Pick 3 other, distinct population members
	while True:
		r1 = random.randrange(len(parents))
		if r1 != idx:
			break
	while True:
		r2 = random.randrange(len(parents))
		if r2 != idx and r2 != r1:
			break
	while True:
		r3 = random.randrange(len(parents))
		if r3 != idx and r3 != r2 and r3 != r1:
			break
	
	child = parents[idx][:]
	j = random.randrange(len(limits))
	if best_idx != None:
		for k in range(len(limits)):
			z = (j + k) % len(limits) + 1
			child[z] += factor * (parents[best_idx][z] - child[z]) + factor * (parents[r2][z] - parents[r3][z])
			if random.random() > cross:
				break
		origin = parents[idx][:]
	else:
		for k in range(len(limits)):
			z = (j + k) % len(limits) + 1
			child[z] = parents[r1][z] + factor * (parents[r2][z] - parents[r3][z])
			if random.random() > cross:
				break
		origin = parents[r1]

	for k in range(len(limits)):
		z = k + 1
		if child[z] < limits[k][0]:
			child[z] = limits[k][0] + random.random() * (origin[z] - limits[k][0])
		
		if child[z] > limits[k][1]:
			child[z] = limits[k][1] + random.random() * (origin[z] - limits[k][1])
	return child
