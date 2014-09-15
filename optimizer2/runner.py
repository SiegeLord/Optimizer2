# Copyright (c) 2014 by Pavel Sountsov
#
# All rights reserved. Distributed under GPL 3.0. For full terms see the file LICENSE.

from subprocess import Popen, PIPE
from optimizer2.common_evolution import *
from optimizer2.array_parser import parse_array
from Queue import Queue, Empty
from threading import Thread, Lock, Event
from signal import SIGTERM

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

class Runner:
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

	def run_all(self, pop):
		pop_idx = 0
		num_done = 0
		while num_done < len(pop):
			while pop_idx < len(pop):
				if self.add_task(pop_idx, pop[pop_idx]):
					pop_idx += 1
				else:
					break

			ret = self.get_task()
			if not ret:
				continue
			idx, indiv = ret
			pop[idx] = indiv
			num_done += 1

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
