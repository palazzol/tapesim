# import kivy module
import kivy
 
# this restrict the kivy version i.e
# below this kivy version you cannot
# use the app or software
kivy.require("1.9.1")
 
# base Class of your App inherits from the App class.
# app:always refers to the instance of your application
from kivy.app import App

from kivy.uix.boxlayout import BoxLayout

# creates the button in kivy
# if not imported shows the error
from kivy.uix.button import Button
 
import pyaudio
import numpy as np

import wave

from math import pi, sin

# Internal class used for each Sample
class Sample:
    def __init__(self, buffer):
        self.buffer0 = buffer.tobytes()
        self.buffer1 = (-buffer).tobytes()
        if buffer[-1] < 0:
            self.do_reverse = 0
        else:
            self.do_reverse = 1

# Fast Lookup of Samples, with sense correction
class AudioGenerator:
    def __init__(self):
        self.samples_per_second = 48000
        # 4800 bps means...
        # 10 samples per bit
        # 12 bits per byte: start, 8 data, 2 stop, 1 idle
        self.amplitude = 30000

        # Single bit buffers, used for buffer generation
        # (Rectangular)
        #self.zero = np.full(10, self.amplitude, dtype='<i2')
        #self.one = np.hstack((np.full(5, self.amplitude, dtype='<i2'),
        #                     np.full(5, -self.amplitude, dtype='<i2')))
        # (Sinusoidal)
        self.zero = (self.amplitude*np.sin(np.linspace(0, 9*np.pi/10, num=10))).astype('<i2')
        self.one = (self.amplitude/2*np.sin(np.linspace(0, 9*np.pi/5, num=10))).astype('<i2')
        # Blank buffer
        self.noaudio = np.full(10, 0, dtype='<i2')

        # The main dict of sample data is here
        self.sample = {}
        self.last_sense = 0

        # Two special patches
        self.addBuffer('blank', np.tile(self.noaudio,12))
        self.addBuffer('idle',  np.tile(np.hstack((self.zero, -self.zero)), 6))
        
        # Byte codes
        for i in range(0, 256):
            self.addBuffer(chr(i))

    def addBuffer(self,name,buffer=None):
        if buffer is None:
            code = ord(name[0])
            # TBD - generate primary buffer here
            sense = 0
            buffer = self.one
            for i in range(0,8):
                if (code >> i) & 0x01 == 1:
                    if sense == 0:
                        buffer = np.hstack((buffer, self.zero))
                    else:
                        buffer = np.hstack((buffer, -self.zero))
                    sense ^= 1
                else:
                    if sense == 0:
                        buffer = np.hstack((buffer, self.one))
                    else:
                        buffer = np.hstack((buffer, -self.one))
            for i in range(0,3):
                if sense == 0:
                    buffer = np.hstack((buffer, self.zero))
                else:
                    buffer = np.hstack((buffer, -self.zero))
                sense ^= 1
        self.sample[name] = Sample(buffer)

    def getBuffer(self, name):
        s = self.sample[name]
        if self.last_sense == 0:
            self.last_sense ^= s.do_reverse
            return s.buffer0
        else:
            self.last_sense ^= s.do_reverse
            return s.buffer1

class HandshakeFlag:
    def __init__(self):
        self._m = 0
        self._s = 0
        self.buffer = [ b'' ] * 0x10
    def MainSignalSecondary(self, buffer):
        self.buffer[self._m] = buffer
        self._m = (self._m+1)%0x10

    def SecondaryAckMain(self):
        self._s = (self._s+1)%0x10

    def MainAckd(self):
        return self._m == self._s
    
    def SecondarySignaled(self):
        if self._m != self._s:
            return self.buffer[self._s]
        else:
            return b''
   
# class in which we are creating the button
class ButtonApp(App):
    def __init__(self):
        self.carrier_on = False
        App.__init__(self)

    def on_start(self):
        self.flag = HandshakeFlag()

        self.sample_rate = 48000
        self.frames_per_buffer = 120

        # Initialize sample buffers
        self.audio = AudioGenerator()

        self.wf = None
        #self.wf = wave.open('wavfile.wav', 'wb')
        #self.wf.setnchannels(1)
        #self.wf.setsampwidth(2)
        #self.wf.setframerate(48000)
        #self.wf.setnframes(120)

        # Define callback for playback (1)
        def callback(in_data, frame_count, time_info, status):
            b = self.flag.SecondarySignaled()
            if b != b'':
                self.flag.SecondaryAckMain()
            elif self.carrier_on:
                b = self.audio.getBuffer('idle')
            else:
                b = self.audio.getBuffer('blank')
            if self.wf:
                self.wf.writeframes(b)
            return (b, pyaudio.paContinue)

        # Instantiate PyAudio and initialize PortAudio system resources (2)
        self.p = pyaudio.PyAudio()

        # Open stream using callback (3)
        self.stream = self.p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=self.sample_rate,
                        output=True,
                        frames_per_buffer=self.frames_per_buffer,
                        stream_callback=callback)

    def build(self):
        # use a (r, g, b, a) tuple
        if self.carrier_on:
            btext = "Carrier Off"
        else:
            btext = "Carrier On"
        self.btn1 = Button(text = btext,
                   font_size ="20sp",
                   background_color =(1, 1, 1, 1),
                   color =(1, 1, 1, 1))
                   #size =(32, 32),
                   #size_hint =(.2, .2),
                   #pos =(200, 250))
        self.btn2 = Button(text ="Send Char",
                   font_size ="20sp",
                   background_color =(1, 1, 1, 1),
                   color =(1, 1, 1, 1))
                   #size =(32, 32),
                   #size_hint =(.2, .2),
                   #pos =(300, 250))
        # bind() use to bind the button to function callback
        self.btn1.bind(on_press = self.btn1callback)
        self.btn2.bind(on_press = self.btn2callback)
        boxlayout = BoxLayout()
        boxlayout.add_widget(self.btn1)
        boxlayout.add_widget(self.btn2)
        return boxlayout

    def btn1callback(self, event):
        if self.carrier_on:
            self.carrier_on = False
            self.btn1.text = "Carrier On"
        else:
            self.carrier_on = True
            self.btn1.text = "Carrier Off"

    def btn2callback(self, event):
        if not self.carrier_on:
            return
        while not self.flag.MainAckd():
            pass
        self.flag.MainSignalSecondary(self.audio.getBuffer('C'))
        self.flag.MainSignalSecondary(self.audio.getBuffer('D'))

    def on_stop(self):
        # Close the stream (5)
        self.stream.close()

        if self.wf:
            self.wf.close()

        # Release PortAudio system resources (6)
        self.p.terminate()

# creating the object root for ButtonApp() class 
root = ButtonApp()
 
# run function runs the whole program
# i.e run() method which calls the target
# function passed to the constructor.
root.run()
