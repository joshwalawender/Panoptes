#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by Josh Walawender on 2012-10-29.
Copyright (c) 2012 . All rights reserved.
"""

import sys
import os
import subprocess
import re
import fnmatch
import numpy
import time
from argparse import ArgumentParser

import IQMon
import MeasureImage

help_message = '''
The help message goes here.
'''


def GetImtype(imageFile):
    RawFile = os.path.abspath(imageFile)
    RawFileDirectory, RawFilename = os.path.split(RawFile)
    RawBasename, RawExt = os.path.splitext(RawFilename)
    DataNightDirectory, DataNightString = os.path.split(os.path.split(RawFileDirectory)[0])
    infoFile = os.path.join(DataNightDirectory, DataNightString, "CR2info", RawBasename+'.info')
    infoFO = open(infoFile, 'r')
    info = infoFO.read()
    lines = info.split("\n")
    infoFO.close()
    imtype = None
    for line in lines:
        IsMatch = re.match("IMTYPE:\s+(\w+)", line)
        if IsMatch:
            imtype = IsMatch.group(1)
    return imtype


def main():
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = ArgumentParser(description="Describe the script")
    ## add flags
    parser.add_argument("-n", "--no-clobber",
        dest="clobber", action="store_false", default=True, 
        help="Delete previous logs and summary files for this night. (default = True)")
    ## add arguments
    parser.add_argument("-d", "--date", 
        dest="date", required=False, default="", type=str,
        help="UT date of night to analyze. (i.e. '2013-08-05')")
    args = parser.parse_args()
    
    
    ##-------------------------------------------------------------------------
    ## Set date to tonight if not specified
    ##-------------------------------------------------------------------------
    now = time.gmtime()
    DateString = time.strftime("%Y-%m-%d", now)
    if not args.date:
        args.date = DateString
    
    ## Set Path to Data for this night
    DataPath = os.path.join("/skycamdata")
    ImagesDirectory = os.path.join(DataPath, args.date, "CR2")
    
    print("Analyzing data for night of {}".format(args.date))
    if os.path.exists(ImagesDirectory):
        print("  Found {}".format(ImagesDirectory))
        ##
        ## Loop Through All Images in Images Directory
        ##
        Files = sorted(os.listdir(ImagesDirectory))
        print("Found {} files in images directory".format(len(Files)))
        if len(Files) >= 1:
            ## Parse filename for date and time
            MatchFilename = re.compile("IMG\d_(\d{4})\.CR2")
            Properties = []
            for File in Files:
                IsMatch = MatchFilename.match(File)
                if IsMatch:
                    filenumber = IsMatch.group(1)
                    try:
                        imtype = GetImtype(os.path.join(ImagesDirectory, File))
                    except:
                        imtype = None
                    if imtype and imtype == "OBJECT":
                        Properties.append([filenumber, File])

            SortedImageFiles   = numpy.array([row[1] for row in sorted(Properties)])
        
            print("{} out of {} files meet selection criteria.".format(len(SortedImageFiles), len(Files)))
            for Image in SortedImageFiles:
                if fnmatch.fnmatch(Image, "*.CR2"):
                    now = time.gmtime()
                    TimeString = time.strftime("%Y/%m/%d %H:%M:%S UT -", now)
                    DateString = time.strftime("%Y%m%dUT", now)

                    if args.clobber and Image == SortedImageFiles[0]:
                        clobber = True
                    else:
                        clobber = False
                    MeasureImage.MeasureImage(os.path.join(ImagesDirectory, Image), clobber=clobber)

#                     ProcessCall = ['python2.7', os.path.join(os.path.expanduser('~'), 'git', 'Panoptes', 'MeasureImage.py')]
#                     if args.clobber and Image == SortedImageFiles[0]:
#                         ProcessCall.append("--clobber")
#                     ProcessCall.append(os.path.join(ImagesDirectory, Image))
#                     print("{} Calling MeasureImage.py with {}".format(TimeString, repr(ProcessCall)))
#                     MIoutput = subprocess.check_output(ProcessCall, stderr=subprocess.STDOUT)
#                     for line in MIoutput.split("\n"):
#                         print(line)
#                     try:
#                         MIoutput = subprocess.check_output(ProcessCall, stderr=subprocess.STDOUT)
#                         for line in MIoutput.split("\n"):
#                             print(line)
#                     except:
#                         print("Call to MeasureImage.py Failed: {0} {1} {2}".format(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
        else:
            print("No image files found in directory: {}".format(ImagesDirectory))
    else:
        print("No Images or Logs directory for this night")

if __name__ == "__main__":
    sys.exit(main())
