# Copyright (c) 2014 by Pavel Sountsov
#
# All rights reserved. Distributed under GPL 3.0. For full terms see the file LICENSE.

from ConfigParser import NoOptionError
from subprocess import Popen, PIPE
from optimizer2.common_evolution import *
from optimizer2.array_parser import parse_array
from Queue import Queue, Empty
from threading import Thread, Lock, Event
from signal import SIGTERM

import random
import time
import shlex
import os

# Threadproc can exit in two conditions.
#
# 1. There was some error (e.g. the runner failed or the output was malformed). This is accompanied by the thread putting an error message on the err_queue
#    Notably, if exit_event is set, the error message is not posted (because when exit_event is set, the processes will be killed by the main thread).
# 2. exit_event is set.
def thread_proc(in_queue, out_queue, err_queue, thread_lock, exit_event, pid_set, cmd_str, res_re, verbose):
	error = ""
	while not exit_event.is_set():
		res = in_queue.get()
		if res is None:
			# We're probably being asked to die
			if exit_event.is_set():
				return
			else:
				error = "Internal error: res is None, but exit event not set?"
				break
		(pop_idx, pop_indiv) = res

		cmd = cmd_str.format(*pop_indiv[1:])
		if verbose:
			print 'Running:', cmd
		args = shlex.split(cmd)

		thread_lock.acquire()
		# The lock was held by the main thread while killing, don't want to spawn a new process at this time
		if exit_event.is_set():
			thread_lock.release()
			return
		proc = Popen(args, stdout=PIPE)
		pid_set.add(proc.pid)
		thread_lock.release()

		out, _ = proc.communicate()

		# The main thread is now killing/finished killing. This PID is about to be/is invalid, so just return
		if exit_event.is_set():
			return

		thread_lock.acquire()
		pid_set.remove(proc.pid)
		thread_lock.release()

		if proc.returncode != 0:
			print out
			error = "'" + cmd + "' returned a non-0 status!"
			break

		thread_lock.acquire()
		if res_re:
			match = res_re.search(out)
			if match:
				l = match.group(1)
			else:
				error = 'Could not parse the output!'
				break
		else:
			l = out.splitlines()[-1]
		thread_lock.release()

		ret = (pop_idx, pop_indiv[:])
		ret[1][0] = float(l)

		out_queue.put(ret)
	if not exit_event.is_set():
		err_queue.put(error)

class Cont:
	def __init__(self, cmd_str, res_re, max_launches, verbose):
		self.cmd_str = cmd_str
		# Shared.
		self.res_re = res_re
		self.num_launches = 0
		# Used to send items to the threads
		self.in_queue = Queue()
		# Used to receive items from the threads
		self.out_queue = Queue()
		# Threads will add to this if there is an error
		self.err_queue = Queue()
		# Lock to access common resources
		self.thread_lock = Lock()
		# Set of pids that are currently running. Shared.
		self.pid_set = set()
		self.exit_event = Event()
		self.verbose = verbose
		self.threads = []
		for _ in range(max_launches):
			args = (self.in_queue, self.out_queue, self.err_queue, self.thread_lock, self.exit_event, self.pid_set, self.cmd_str, self.res_re, self.verbose)
			t = Thread(target = thread_proc, args = args)
			t.daemon = True
			t.start()
			self.threads.append(t)

	def add_task(self, pop_idx, pop_indiv):
		if self.num_launches >= len(self.threads):
			return False
		self.in_queue.put((pop_idx, pop_indiv))
		self.num_launches += 1
		return True

	def get_task(self):
		if self.num_launches == 0:
			return None

		# We poll this to prevent the main thread from not-responding to signal
		# handlers. Also, to catch errors.
		while True:
			try:
				err = self.err_queue.get(False)
				self.kill_all()
				raise Exception(err)
			except Empty:
				pass
			try:
				res = self.out_queue.get(False, 1.0)
				break
			except Empty:
				pass
		self.num_launches -= 1
		return res

	def kill_all(self):
		self.exit_event.set()
		self.thread_lock.acquire()
		for pid in self.pid_set:
			try:
				os.kill(pid, SIGTERM)
			except OSError:
				# It is possible that the pid died before we got to it
				pass
		self.thread_lock.release()
		for thread in self.threads:
			thread.join(0.1)
			self.in_queue.put(None)


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
