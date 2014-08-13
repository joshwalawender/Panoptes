#!/usr/bin/env python
# encoding: utf-8
"""
Monitor.py

Created by Josh Walawender on 2013-07-25.
Copyright (c) 2013 __MyCompanyName__. All rights reserved.
"""

from __future__ import division, print_function

import sys
import os
from argparse import ArgumentParser
import re
import time
import subprocess


help_message = '''
The help message goes here.
'''


def GetImtype(imageFile):
    RawFile = os.path.abspath(imageFile)
    RawFileDirectory, RawFilename = os.path.split(RawFile)
    RawBasename, RawExt = os.path.splitext(RawFilename)
    DataNightDirectory, DataNightString = os.path.split(os.path.split(RawFileDirectory)[0])
    infoFile = os.path.join(DataNightDirectory, DataNightString, "CR2info", RawBasename+'.info')

    if not os.path.exists(infoFile):
        time.sleep(2)

    if os.path.exists(infoFile):
        infoFO = open(infoFile, 'r')
        info = infoFO.read()
        lines = info.split("\n")
        infoFO.close()
        imtype = None
        for line in lines:
            IsMatch = re.match("IMTYPE:\s+(\w+)", line)
            if IsMatch:
                imtype = IsMatch.group(1)
        if not imtype:
            print("  Could not read image type from info file: {}".format(infoFile))
        return imtype
    else:
        print("  Could not find image info file: {}".format(infoFile))
        return None


def main(argv=None):  
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = ArgumentParser(description="Describe the script")
    ## add arguments
    args = parser.parse_args()
    telescope = "Panoptes"
    
    ##-------------------------------------------------------------------------
    ## Set date to tonight
    ##-------------------------------------------------------------------------
    now = time.gmtime()
    DateString = time.strftime("%Y-%m-%d", now)

    ##-------------------------------------------------------------------------
    ## Set data path
    ##-------------------------------------------------------------------------
    PathForDate = os.path.join("/skycamdata", DateString)
    DataPath = os.path.join(PathForDate, "CR2")


    ##-------------------------------------------------------------------------
    ## Look for Pre-existing Files
    ##-------------------------------------------------------------------------
    if not os.path.exists(PathForDate): os.mkdir(PathForDate)
    if not os.path.exists(DataPath): os.mkdir(DataPath)
    PreviousFiles = os.listdir(DataPath)
    PreviousFilesTime = time.gmtime()

    ##-------------------------------------------------------------------------
    ## Operation Loop
    ##-------------------------------------------------------------------------
    PythonString = os.path.join("/usr", "bin", "python")
    MeasureImageString = os.path.join(os.path.expanduser('~'), "git", "Panoptes", "MeasureImage.py")
    Operate = True
    while Operate:
        ## Set date to tonight
        now = time.gmtime()
        nowDecimalHours = now.tm_hour + now.tm_min/60. + now.tm_sec/3600.
        DateString = time.strftime("%Y-%m-%d", now)
        TimeString = time.strftime("%Y-%m-%d %H:%M:%S -", now)
        
        Files = os.listdir(DataPath)
        FilesTime = now
        
        time.sleep(1)
                
        if len(Files) > len(PreviousFiles):
            for File in Files:
                FileFound = False
                for PreviousFile in PreviousFiles:
                    if File == PreviousFile:
                        FileFound = True
                if not FileFound:
                    if re.match("IMG0_\d{4}\.CR2", File):
                        print("New image File Found:  %s" % File)
                        imtype = GetImtype(os.path.join(DataPath, File))
                        if not imtype:
                            print("  Waiting 10 seconds for info file to be written.")
                            time.sleep(10)  ## Wait for info file to be written
                            imtype = GetImtype(os.path.join(DataPath, File))
                        if not imtype:
                            print("  Waiting 20 seconds for info file to be written.")
                            time.sleep(20)  ## Wait for info file to be written
                            imtype = GetImtype(os.path.join(DataPath, File))
                        if imtype and imtype == "OBJECT":
                            ProcessCall = [PythonString, MeasureImageString, os.path.join(DataPath, File)]
                            print("  %s Calling MeasureImage.py with %s" % (TimeString, ProcessCall[2:]))
                            try:
                                MIoutput = subprocess.check_output(ProcessCall, stderr=subprocess.STDOUT, universal_newlines=True)
                                print("  Call to MeasureImage.py Succeeded")
                            except subprocess.CalledProcessError as e:
                                print("  Call to MeasureImage.py Failed")
                                print("  Command: {}".format(e.command))
                                print("  Returncode: {}".format(e.returncode))
                                print("  Output: {}".format(e.output))
                            except:
                                print("  Call to MeasureImage.py Failed: {0} {1} {2}".format(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
                        else:
                            print("  File ImType is {}.  MeasureImage not called.".format(imtype))
        PreviousFiles = Files
        PreviousFilesTime = now
        
        ##-------------------------------------------------------------------------
        ## Create Link to Tonight HTML File
        ##-------------------------------------------------------------------------
        linkTarget = os.path.join(os.path.expanduser('~'), "IQMon", "Logs", DateString+"_Panoptes.html")
        linkFile = os.path.join(os.path.expanduser('~'), "IQMon", "Logs", "tonight.html")
        ## If the tonight.html file already exists, remove it.
        if os.path.exists(linkFile):
            if (os.readlink(linkFile) != linkTarget) and (os.path.exists(linkTarget)):
                print('Removing old tonight.html file')
                os.remove(linkFile)
        ## Use os.symlink to link tonight.html to the correct file
        if not os.path.exists(linkFile):
            try:
                print('Making tonight.html symlink')
                os.symlink(linkTarget, linkFile)
            except:
                print("Could not create link to tonight's data.")
                for element in sys.exc_info():
                    print(element)

        time.sleep(5)
        if nowDecimalHours > 17.0:
            Operate = False


if __name__ == "__main__":
    sys.exit(main())
