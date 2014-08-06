# Copyright (c) 2014 by Pavel Sountsov
#
# All rights reserved. Distributed under GPL 3.0. For full terms see the file LICENSE.

import ast

def error_message(string):
	return 'Could not parse "' + string + '" as a list of numbers: "[val0, val1, ...]"'

def parse_array(string):
	ret = []
	try:
		lst = ast.literal_eval(string)
		if not type(lst) is list:
			raise Exception(error_message(string))

		for v in lst:
			try:
				ret.append(float(v))
			except ValueError:
				raise Exception(error_message(string))
	except (ValueError, SyntaxError):
		# Try the space separated version
		for s in string[1:-1].split():
			try:
				ret.append(float(s))
			except ValueError:
				raise Exception(error_message(string))

	return ret
