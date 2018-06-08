#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# signal-gen.py
# 
# Output test signals via ALSA, e. g. for measuring frequency and step responses of audio
# equipment.
#
# Copyright 2018 Andre Plötze
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from __future__ import division
from __future__ import print_function
import alsaaudio
import itertools
import numpy as np
import struct

"""
A class implementing buffered audio I/O.
"""
class Audio:
	
	"""
	Initializes the audio buffer.
	"""
	def __init__(self, low_res = False):
		self.__stride = 4
		self.__low_res = low_res
		self.__pre_post = 0
	
	"""
	Serialize the audio samples from an array of integers into a binary string.
	"""
	def serialize(self, a):
		s = ""
		fmt = "<h" if self.__low_res else ">i"
		
		# Process each element.
		for elem in a:
			s += struct.pack(fmt, elem)
		
		return s
	
	"""
	Deserialize the audio samples from a binary string into an array of integers.
	"""
	def deserialize(self, s):
		endianness, fmt, the_stride = ("<", "h", self.__stride // 2) if self.__low_res else (">", "i", self.__stride)
		return struct.unpack(endianness + (fmt * (len(s) // the_stride)), s)
	
	"""
	Normalize the audio samples from an array of integers into an array of floats with unity level.
	"""
	def normalize(self, data, max_val):
		data = np.array(data)
		fac = 1.0 / max_val
		data = fac * data
		return data
	
	"""
	Denormalize the data from an array of floats with unity level into an array of integers.
	"""
	def denormalize(self, data, max_val):
		fac = 1.0 * max_val
		data = np.array(data)
		data = np.clip(data, -1.0, 1.0)
		data = (fac * data).astype(np.int64)
		return data

"""
This class implements a linear congruency generator (LCG).
"""
class LCG:
    
    """
    The class constructor initializes the LCG with a seed.
    """
    def __init__(self, seed):
        scale = 64979
        offset = 83
        self.__a = 7 ** 5
        self.__b = 0
        self.__c = (2 ** 31) - 1
        self.__state = (int(scale * seed) + offset) % self.__c
    
    """
    This special method turns this class into an iterator.
    """
    def __iter__(self):
        return self
    
    """
    This is the method an iterator must implement.
    """
    def next(self):
        self.__state = ((self.__a * self.__state) + self.__b) % self.__c
        return self.__state
    
    """
    This method returns the c value of the LCG.
    """
    def get_c(self):
        return self.__c
    
    """
    This method draws n samples in the interval [0, 1] from a uniform distribution.
    """
    def draw_uniform(self, n = 1):
        return np.array(list(itertools.islice(self, int(n)))) / self.__c

# Program entry point.
if __name__ == "__main__":
	
	# Prepare for audio I/O.
	audio = Audio()
	rate = 96000
	num = rate // 50
	
	# Pre-generate samples.
	lcg = LCG(1337)
	silence = np.zeros(rate)
	plusone = np.ones(rate)
	minusone = -np.ones(rate)
	noise = lcg.draw_uniform(n = rate)
	ndata = np.concatenate((silence, noise, silence, plusone, silence, minusone, silence, plusone, minusone, silence))
	
	# Prepare for output.
	outp = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, alsaaudio.PCM_NORMAL)
	outp.setchannels(1)
	outp.setrate(rate)
	outp.setformat(alsaaudio.PCM_FORMAT_S32_BE)
	outp.setperiodsize(num * 4)
	
	# Output test signal in an infinite loop.
	while True:
		rdata = np.copy(ndata)
		
		# Proceed onto the next chunk until we wrote it all out.
		while len(rdata) > 0:
			ldata, rdata = rdata[0 : num], rdata[num : ]
			pdata = audio.denormalize(ldata, 0x7fffffff)
			data = audio.serialize(pdata)
			outp.write(data)

