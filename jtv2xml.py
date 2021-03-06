#!/usr/bin/python
#-*- coding: utf-8 -*-
# =======================================================================================================
# PDT file format:
# The file is always starts with "JTV 3.x TV Program Data" folowed by three characters with the code 0Ah. 
# Starting from 01Ah offset there are the records with the variable length:
#  * 2 bytes - the number of characters in the TV-show title
#  * TV-show title
#
# NDX file format:
# The first two bytes is the number of records in .ndx file. Than there are 12 bytes records:
#   * First two bytes is always 0
#   * Eight bytes of FILETIME structure (Contains a 64-bit value representing the number of 
#                                        100-nanosecond intervals since January 1, 1601 (UTC).)
#   * Two bytes - the offset pointer to TV-show characters number title in .pdt file.
# =======================================================================================================
import re
import sys
import struct
import datetime
from zipfile import *

jtvzip = 'jtv.zip'
xmltv = 'xmltv.xml'
timezone = '+0200'
zip_encode = 'cp866'
#zip_encode = 'utf-8'
pdt_encode = 'cp1251'


def ft_to_dt(ft):
  microseconds = ft / 10
  seconds, microseconds = divmod(microseconds, 1000000)
  days, seconds = divmod(seconds, 86400)
  return datetime.datetime(1601, 1, 1) + datetime.timedelta(days, seconds, microseconds)


def read_jtv_channels(jtvzip):
  jtv = ZipFile(jtvzip, 'r')
  channels = []

  for item in jtv.namelist():
    if '.ndx' in item:
      if zip_encode == 'utf-8':
        channels.append(re.compile('(.*).ndx$').match(item).group(1))
      else: 
        channels.append(re.compile('(.*).ndx$').match(item).group(1).decode(zip_encode).encode('utf-8'))

  jtv.close()
  return channels


def write_xml_channels(channels, xmltv):
  chcount = 1000
  with open(xmltv, 'w') as xmlfile:
    xmlfile.write('<?xml version="1.0" encoding="utf-8" ?>\n')
    for channel_name in channels:
      chcount += 1
      xmlfile.write('<channel id="%d">\n' % chcount)
      if zip_encode == 'utf-8':
        xmlfile.write('  <display-name>%s</dispay-name>\n' % channel_name.encode('utf-8'))
      else:
        xmlfile.write('  <display-name>%s</dispay-name>\n' % channel_name)
      xmlfile.write('</channel>\n')
  xmlfile.close()


def write_xml_schedule(chname, chid, title, str_time, end_time):
  chcount = 0
  with open(xmltv, 'a') as xmlfile:
    xmlfile.write('<programme start="%s %s" stop="%s %s" channel="%d">\n' % (str_time, timezone, end_time, timezone, chid))
    xmlfile.write('  <title lang="ru">%s</title>\n</programme>\n' % title)
  xmlfile.close()


def read_jtv(chname, chid):
  if zip_encode == 'utf-8':
    ndx = (chname + '.ndx')
    pdt = (chname + '.pdt')
  else:
    ndx = (chname + '.ndx').decode('utf-8').encode(zip_encode)
    pdt = (chname + '.pdt').decode('utf-8').encode(zip_encode)

  with open('jtv/' + ndx, 'rb') as ndx:
    with open('jtv/' + pdt, 'rb') as pdt:
      number = struct.unpack('h', ndx.read(2))[0] # Number of records in .ndx file
      
      for i in range(number):
        str_time = 0 
        end_time = 0

        ndx.seek((i + 1) * 12 - 8)
        str_time = struct.unpack('Q', ndx.read(8))[0] # Get program start time in FILETIME format

        if i < (number - 1):
          ndx.seek((i + 2) * 12 - 8)
          end_time = struct.unpack('Q', ndx.read(8))[0]
        else:
          end_time = str_time # For the last TV-show we know only the start time.
        
        ndx.seek((i + 1) * 12)
        pdt_offset = struct.unpack('H', ndx.read(2))[0] # Offset pointer to .pdt file

        pdt.seek(pdt_offset)
        poffset = struct.unpack('H', pdt.read(2))[0] # Get TV-show's title characters number.

        chars = []
        title = str()
        
        try:
          for j in range(poffset):
            char = struct.unpack('c', pdt.read(1))[0]
            chars.append(char.decode(pdt_encode))
          title = title.join(chars).encode('utf-8')
        except Exception, e:
          print '\n\n\n\tSomething went wrong!\nFile "%s.pdt" is not fully decoded!\n' % chname
          print 'Error message:\n%s\n\nDebug information:' % e
          print 'chname - %s\nndx_offset  - %X\npdt_offset  - %X\npdt_namelen - %X\nfiletime   - %X\n'\
                 % (chname, 12*i+12, pdt_offset, poffset, str_time)
          ndx.close()
          pdt.close()
          break

        str_time = format(ft_to_dt(str_time), '%Y%m%d%H%M%S')
        end_time = format(ft_to_dt(end_time), '%Y%m%d%H%M%S')
        write_xml_schedule(chname, chid, title, str_time, end_time)
  ndx.close()
  pdt.close()


def main():
  ZipFile('jtv.zip', 'r').extractall('jtv')
  channels = read_jtv_channels(jtvzip)
  write_xml_channels(channels, xmltv)

  for i in range(len(channels)):
    sys.stdout.write("*")
    sys.stdout.flush()
    read_jtv(channels[i], i+1001)
  sys.stdout.write("\n")
  print "Done!"

if __name__ == '__main__':
  main()
