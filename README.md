# audio-tools

Tools for audio work, especially for measuring impulse responses of audio equipment.

Usage
-----

Outputting a test signal through your default ALSA sound device:

`python signal-gen.py`

On Fedora, this requires the package `python-alsaaudio` installed.

`sudo dnf install python-alsaaudio`

On other distributions, the package name may be slightly different.

Deriving an impulse response (`ir.wav`) from a step response (`sr.wav`).

`python sr-to-ir.py sr.wav ir.wav`

The input file must be a monophonic 16-bit RIFF WAVE file, otherwise unexpected things may happen.

The impulse response will probably be quite noisy since the differentiation strongly amplifies high frequency components of the signal, which are generally noise. You may restrict the frequency range of the produced impulse response to the audible (20 Hz to 20 kHz) range to achieve a better signal-to-noise ratio (SNR) by appending an optional parameter called `postprocess`, although this will slightly reduce the accuracy of the impulse response produced.

`python sr-to-ir.py sr.wav ir.wav postprocess`

