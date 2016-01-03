#!/usr/bin/python

# googletts
# Created by Matt Dyson (mattdyson.org)
# http://mattdyson.org/blog/2014/07/text-to-speech-on-a-raspberry-pi-using-google-translate/
# Some inspiration taken from http://danfountain.com/2013/03/raspberry-pi-text-to-speech/

# Version 1.0 (12/07/14)

# Process some text input from our arguments, and then pass them to the Google translate engine
# for Text-To-Speech translation in nicely formatted chunks (the API cannot handle more than 100
# characters at a time).
# Splitting is done first by any punctuation (.,;:) and then by splitting by the MAX_LEN defined
# below.
# mpg123 is required for playing the resultant MP3 file that is returned by Google TTS

from subprocess import call
import getopt
import sys
import time
import os
import re
import urllib
import pprint
import hashlib
import pycurl

isVerbose = False
cachePath = 'cache/'

#
# debug message
#
def debug(message):
  global isVerbose
  if isVerbose:
    print message

#
# usage message
#
def usage():
  print "Usage: tts.py [OPTION] -t <text>\n"
  print "Mandatory arguments."
  print "  --text text to speech"
  print "Optional arguments."
  print "  --engine     engine for rendering google or voxygen (default: google)"
  print "  --language   language of TTS (default: en)"
  print "  --in-file    text file to speech"
  print "  --out-file   out file to render"
  print "  --max-len    max len of segments (default: 100)"
  print "  --cache-path Path for cache files"
  print "  --no-cache   No cache"
  print "  --verbose    verbose"
  print 'ex: tts.py -l en -t "Hello world" -v'

#
# call google tts engine
#
def callGoogle(part, currentLanguage, currentVoice):
  global cachePath

  url = "http://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=%s&q=%s" % (currentLanguage, urllib.quote(part))
  hashName = hashlib.md5(url).hexdigest()
  outFile = tempPath + 'tts_' + hashName + '.mp3'

  debug('Call Google %s to %s' % (url, outFile))

  with open(outFile, 'wb') as buffer:
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.HEADER, False)
    c.setopt(c.FOLLOWLOCATION, True)
    c.setopt(c.USERAGENT, 'iTunes/9.0.3 (Macintosh; U; Intel Mac OS X 10_6_2; en-ca)')
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()

    return outFile

#
# call voxygen tts engine
#
def callVoxygen(part, currentLanguage, currentVoice):
  global cachePath

  if currentVoice == None:
    currentVoice = 'Agnes'
  url = "https://www.voxygen.fr/sites/all/modules/voxygen_voices/assets/proxy/index.php?method=redirect&text=%s&voice=%s&ts=%s" % (urllib.quote(part), urllib.quote(currentVoice), str(int(time.time())))

  hashName = hashlib.md5(url).hexdigest()
  outFile = tempPath + 'tts_' + hashName + '.mp3'

  debug('Call Voxygen %s to %s' % (url, outFile))

  with open(outFile, 'wb') as buffer:
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.HEADER, False)
    c.setopt(c.FOLLOWLOCATION, True)
    c.setopt(c.REFERER, 'http://voxygen.fr/fr')
    c.setopt(c.USERAGENT, 'iTunes/9.0.3 (Macintosh; U; Intel Mac OS X 10_6_2; en-ca)')
    c.setopt(c.COOKIE, 'has_js=1')
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()

    return outFile

#
# main
#
def main(argv):
  global isVerbose, MAX_LEN, cachePath, tempPath

  # Maximum length of a segment to send to Google for TTS
  MAX_LEN = 100
  # Default language to use with TTS - this won't do any translation, just the voice it's spoken with
  currentLanguage = "en"
  # Default engine for TTS
  currentEngine = "google"
  currentOutfile = None
  currentInfile = None
  currentVoice = None
  noCache = False
  sText = ''

  try:
    opts, args = getopt.getopt(argv,"hvV:m:l:i:o:e:t:",["help","no-cache","cache-path=", "engine=", "out-file=", "in-file=", "max-len=", "verbose", "voice=", "text="])
  except getopt.GetoptError as err:
    print str(err)
    usage()
    sys.exit(2)
  for opt, arg in opts:
    if opt == '-h':
      usage()
      sys.exit()
    elif opt in ("-l", "--language"):
      currentLanguage = arg
    elif opt in ("-t", "--text"):
      sText = arg.strip()
    elif opt in ("-e", "--engine"):
      currentEngine = arg
    elif opt in ("-o", "--out-file"):
      currentOutfile = arg
    elif opt in ("-i", "--in-file"):
      currentInfile = arg
    elif opt in ("-m", "--max-len"):
      MAX_LEN = arg
    elif opt in ("-v", "--verbose"):
      isVerbose = True
    elif opt in ("-V", "--voice"):
      currentVoice = arg
    elif opt in ("-V", "--cache-path"):
      cachePath = arg
    elif opt in ("-c", "--no-cache"):
      noCache = True

  if sText=="":
    print "text do not empty!"
    sys.exit()

  if currentEngine not in ("google" "voxygen"):
    print "unknow %s engine!" % (currentEngine)
    sys.exit()

  tempPath = '/tmp/'

  if not os.path.exists(cachePath):
    os.makedirs(cachePath)

  debug('Use engine %s with %s language' % (currentEngine, currentLanguage))

  # Split our full text by any available punctuation
  parts = re.split("[\.\,\;\:]", sText)

  # The final list of parts to send to engine TTS
  processedParts = []

  while len(parts)>0: # While we have parts to process
    part = parts.pop(0) # Get first entry from our list

    if len(part)>MAX_LEN:
      # We need to do some cutting
      cutAt = part.rfind(" ",0,MAX_LEN) # Find the last space within the bounds of our MAX_LEN

      cut = part[:cutAt]

      # We need to process the remainder of this part next
      # Reverse our queue, add our remainder to the end, then reverse again
      parts.reverse()
      parts.append(part[cutAt:])
      parts.reverse()
    else:
      # No cutting needed
      cut = part

    cut = cut.strip() # Strip any whitespace
    if cut is not "": # Make sure there's something left to read
      # Add into our final list
      processedParts.append(cut.strip())

  hashName = hashlib.md5(currentEngine + currentLanguage + str(currentVoice) + sText).hexdigest()
  outFile = cachePath + hashName + '.mp3'

  if not os.path.isfile(outFile) or noCache==True:
    partList = []
    for part in processedParts:
      if currentEngine=="google":
        hashPart = callGoogle(part, currentLanguage, currentVoice)
      elif currentEngine=="voxygen":
        hashPart = callVoxygen(part, currentLanguage, currentVoice)

      partList.append(hashPart)

    fileList = []
    for partName in partList:
      fileList.append(partName)
    fileList = '|'.join(fileList)

    debug('build final file %s' % outFile)

    callList = ["avconv", "-v", "1", "-y", "-i", "concat:" + fileList, "-acodec", "copy", outFile]
    call(callList)
  else :
    debug("get from cache %s" % outFile)

  if currentOutfile==None:
    debug("play by mpg123")
    call(["mpg123", "-q", outFile])
  else:
    debug("write file in %s" % (currentOutfile))
    call(["cp", outFile, currentOutfile])

if __name__ == "__main__":
  main(sys.argv[1:])