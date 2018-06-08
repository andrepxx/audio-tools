#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# sr-to-ir.py
#
# Derive an impulse response (IR) from a step resonse (SR) using numeric differentiation
# via the central-difference formula.
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
# This program reads and writes 16 bit monophonic WAV files.
#
# Usage: python sr-to-ir.py [step.wav] [impulse.wav] [postprocess]
#
# [step.wav]: Input RIFF WAVE file containing the step response.
#
# [inpulse.wav]: Output RIFF WAVE file which will contain the impulse response.
#
# [postprocess]: Optional third parameter "postprocess", which restricts the spectrum of
#                the generated output to the audible frequency range (20 Hz to 20 kHz) in
#                order to achieve a lower noise floor at the expense of slightly less
#                precise processing.
#

from __future__ import division
import numpy as np
import struct
import sys
import wave

"""
A class implementing wave file I/O.
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
Derives an impulse response.
"""
def derive(ir):
	der = []
	n = len(ir)
	der.append(0.0)

	# Calculate central differences.
	for i in range(1, n - 1):
		der.append(ir[i + 1] - ir[i - 1])

	der.append(0.0)
	return np.array(der)

# Program entry point.
if __name__ == "__main__":
	
	# Check if enough arguments are passed.
	if len(sys.argv) < 3:
		pass
	else:
		# Prepare audio processing and open wave files.
		audio = Audio(low_res = True)
		in_wav = wave.open(sys.argv[1], "rb")
		out_wav = wave.open(sys.argv[2], "wb")
		post_process = False
		
		# Check if there is a fourth argument.
		if len(sys.argv) > 3:
			
			# Check if we should perform post-processing.
			if sys.argv[3] == "postprocess":
				post_process = True
		
		# Read wave parameters and start reading data.
		params = in_wav.getparams()
		out_wav.setparams(params)
		buf = in_wav.readframes(8192)
		data = []
		
		# Read more data into buffer until end of file.
		while len(buf) > 0:
			data.append(buf)
			buf = in_wav.readframes(8192)
		
		# Make sure we do not forget the last chunk.
		data.append(buf)
		ndata = []
		
		# Normalize and concatenate all buffers.
		for buf in data:
			pbuf = audio.deserialize(buf)
			nbuf = audio.normalize(pbuf, 0x7fff)
			ndata.extend(nbuf)
		
		# Calculate the derivative.
		ndata = derive(ndata)
		data_length = len(ndata)
		
		# Perform optional post-processing on the impulse response.
		if post_process:
			
			# Zero-pad the signal to prevent aliasing.
			zeros = np.zeros_like(ndata)
			ndata = np.append(ndata, zeros)
			
			# Calculate the Fourier transform.
			samplerate = in_wav.getframerate()
			samplerate_inv = 1.0 / samplerate
			ndata_fft = np.fft.fft(ndata)
			n = len(ndata_fft)
			freqs = np.fft.fftfreq(n, samplerate_inv)
			
			# Set the Fourier transform to zero if frequency is outside the audible range.
			for i in range(0, len(freqs)):
				freq = np.absolute(freqs[i])
				
				# If Frequency is inaudible, clear this frequency band.
				if (freq < 20.0) | (freq > 20000.0):
					ndata_fft[i] = 0.0
			
			# Calculate the inverse Fourier transform.
			ndata_ifft = np.fft.ifft(ndata_fft)
			ndata = np.real(ndata_ifft)
		
			# Truncate off aliased IFFT values.
			ndata = ndata[: data_length]
		
		# Scale samples into unit range.
		ndata_abs = np.absolute(ndata)
		peak = np.max(ndata_abs)
		scale = 1.0 / peak
		ndata *= scale
		data = []
		
		# Convert all data into binary format.
		for i in range(0, len(ndata), 8192):
			nbuf = ndata[i : i + 8192]
			pbuf = audio.denormalize(nbuf, 0x7fff)
			buf = audio.serialize(pbuf)
			data.append(buf)
		
		# Write the result.
		for buf in data:
			out_wav.writeframes(buf)
		
		# Close the file descriptors.
		out_wav.close()
		in_wav.close()

