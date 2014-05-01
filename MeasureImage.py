#!/usr/bin/env python
# encoding: utf-8
"""
MeasureImage.py

Created by Josh Walawender on 2013-07-25.
Copyright (c) 2013. All rights reserved.
"""

from __future__ import division, print_function

import sys
import os
from argparse import ArgumentParser
import re
import datetime
import math
import time
import subprocess

import ephem
import astropy.units as u
import astropy.io.fits as fits

import IQMon


##-------------------------------------------------------------------------
## Read Skycam Info
##-------------------------------------------------------------------------
def ReadSkycamInfo(RawFile, FitsFile):
    if not os.path.exists(RawFile):
        raise IOError("Unable to find input file: %s" % RawFile)
    RawFileDirectory, RawFilename = os.path.split(RawFile)
    RawBasename, RawExt = os.path.splitext(RawFilename)
    NightDirectory = os.path.split(RawFileDirectory)[0]
    DataNightString = os.path.split(os.path.split(RawFileDirectory)[0])[1]
    InfoDirectory = os.path.join(NightDirectory, "CR2info")
    InfoFile = os.path.join(InfoDirectory, RawBasename+".info")
    try:
        infoFO = open(InfoFile, 'r')
        infolines = infoFO.read().split("\n")
    except:
        raise

    hdulist = fits.open(FitsFile, mode='update', ignore_missing_end=True)
    for line in infolines:
        IsOBJECT = re.match("TARGETDESCRIPTION:\s*(\w+)", line)
        if IsOBJECT: hdulist[0].header['OBJECT'] = IsOBJECT.group(1)
        IsEXPTIME = re.match("SHUTTER:\s*(\d+\.?\d*)\ssec", line)
        if IsEXPTIME: hdulist[0].header['EXPTIME'] = IsEXPTIME.group(1)
        IsRA = re.match("RA:\s*(\d+\.?\d*)\sdeg", line)
        if IsRA:
            RAdecimalhours = float(IsRA.group(1))/15.
            RAh = int(math.floor(RAdecimalhours))
            RAm = int(math.floor((RAdecimalhours - RAh)*60.))
            RAs = ((RAdecimalhours - RAh)*60. - RAm)*60.
            hdulist[0].header['RA'] = "{:02d}:{:02d}:{:04.1f}".format(RAh, RAm, RAs)
        IsDEC = re.match("DEC:\s*(\-?\d+\.?\d*)\sdeg", line)
        if IsDEC:
            DECdecimal = float(IsDEC.group(1))
            DECd = int(math.floor(DECdecimal))
            DECm = int(math.floor((DECdecimal - DECd)*60.))
            DECs = ((DECdecimal - DECd)*60. - DECm)*60.
            hdulist[0].header['DEC'] = "{:02d}:{:02d}:{:04.1f}".format(DECd, DECm, DECs)
        IsUTSTART = re.match("UT_START:\s*(\d+\.?\d*)\shr", line)
        if IsUTSTART:
            UTdecimal = float(IsUTSTART.group(1))
            UTh = int(math.floor(UTdecimal))
            UTm = int(math.floor((UTdecimal - UTh)*60.))
            UTs = ((UTdecimal - UTh)*60. - UTm)*60.
            dateObs = "{}T{:02d}:{:02d}:{:04.1f}".format(DataNightString, UTh, UTm, UTs)
            hdulist[0].header['DATE-OBS'] = dateObs
    hdulist[0].header['LAT-OBS'] = 19.53602
    hdulist[0].header['LONG-OBS'] = -155.57608
    hdulist[0].header['ALT-OBS'] = 3400
    hdulist.flush()
    hdulist.close()


##-------------------------------------------------------------------------
## Main Program
##-------------------------------------------------------------------------
def main():
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = ArgumentParser(description="Describe the script")
    ## add flags
    parser.add_argument("-v", "--verbose",
        action="store_true", dest="verbose",
        default=False, help="Be verbose! (default = False)")
    parser.add_argument("-c", "--clobber",
        action="store_true", dest="clobber",
        default=False, help="Delete previous logs and summary files for this image. (default = False)")
    ## add arguments
    parser.add_argument("filename",
        type=str,
        help="File Name of Input Image File")
    args = parser.parse_args()
    
    ##-------------------------------------------------------------------------
    ## Deconstruct input filename in to path, filename and extension
    ##-------------------------------------------------------------------------
    RawFile = os.path.abspath(args.filename)
    if not os.path.exists(RawFile):
        raise IOError("Unable to find input file: %s" % RawFile)
    RawFileDirectory, RawFilename = os.path.split(RawFile)
    RawBasename, RawExt = os.path.splitext(RawFilename)
    DataNightDirectory, DataNightString = os.path.split(os.path.split(RawFileDirectory)[0])
    skycamJPEGfile = os.path.join(DataNightDirectory, DataNightString, "JPEG", RawFilename+'.jpeg')

    ##-------------------------------------------------------------------------
    ## Establish IQMon Configuration
    ##-------------------------------------------------------------------------
    config = IQMon.Config()


    ##-------------------------------------------------------------------------
    ## Create Telescope Object
    ##-------------------------------------------------------------------------
    tel = IQMon.Telescope()
    tel.name = "Panoptes"
    tel.longName = "Panoptes"
    tel.focalLength = 85.*u.mm
    tel.pixelSize = 4.6*u.micron     ## Need to determine correct pixel size
    tel.aperture = 60.7*u.mm
    tel.gain = 1.6 / u.adu           ## Need to determine correct gain
    tel.unitsForFWHM = 1.*u.pix
    tel.ROI = "[1361:3409,565:2613]"  # Raw Image Size is 4770,3178
    tel.thresholdFWHM = 3.0*u.pix
    tel.thresholdPointingErr = 60.0*u.arcmin
    tel.thresholdEllipticity = 0.30*u.dimensionless_unscaled
    tel.pixelScale = tel.pixelSize.to(u.mm)/tel.focalLength.to(u.mm)*u.radian.to(u.arcsec)*u.arcsec/u.pix
    tel.fRatio = tel.focalLength.to(u.mm)/tel.aperture.to(u.mm)
    tel.SExtractorParams = {'PHOT_APERTURES': 6.0,
                            'SEEING': 3.5,
                            'SATUR_LEVEL': 30000.,
                            'FILTER': 'N',
                            }
    tel.pointingMarkerSize = 10*u.arcmin
    ## Define Site (ephem site object)
    tel.site = ephem.Observer()
    tel.CheckUnits()
    tel.DefinePixelScale()

    ##-------------------------------------------------------------------------
    ## Create IQMon.Image Object
    ##-------------------------------------------------------------------------
    image = IQMon.Image(RawFile, tel, config)  ## Create image object

    ##-------------------------------------------------------------------------
    ## Create Filenames
    ##-------------------------------------------------------------------------
    IQMonLogFileName = os.path.join(config.pathLog, DataNightString+"_"+tel.name+"_IQMonLog.txt")
    htmlImageList = os.path.join(config.pathLog, DataNightString+"_"+tel.name+".html")
    summaryFile = os.path.join(config.pathLog, DataNightString+"_"+tel.name+"_Summary.txt")
    FullFrameJPEG = os.path.join(DataNightString, image.rawFileBasename+"_full.jpg")
    CropFrameJPEG = os.path.join(DataNightString, image.rawFileBasename+"_crop.jpg")
    BackgroundJPEG = os.path.join(DataNightString, image.rawFileBasename+"_bkgnd.jpg")
    if not os.path.exists(os.path.join(config.pathPlots, DataNightString)):
        os.mkdir(os.path.join(config.pathPlots, DataNightString))
    if args.clobber:
        if os.path.exists(IQMonLogFileName): os.remove(IQMonLogFileName)
        if os.path.exists(htmlImageList): os.remove(htmlImageList)
        if os.path.exists(summaryFile): os.remove(summaryFile)


    ##-------------------------------------------------------------------------
    ## Perform Actual Image Analysis
    ##-------------------------------------------------------------------------
    image.MakeLogger(IQMonLogFileName, args.verbose)
    image.logger.info("###### Processing Image:  %s ######", RawFilename)

    image.logger.info("Converting from CR2 to FITS (green channel only).")
    image.workingFile = os.path.join(config.pathTemp, image.rawFileBasename+'.fits')
    if os.path.exists(image.workingFile): os.remove(image.workingFile)
    convertCommand = '/skycam/soft/CR2toFITSg '+image.rawFile+' '+image.workingFile
    image.logger.debug('  Running: {}'.format(convertCommand))
    try:
        result = subprocess.check_call(convertCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except:
        image.logger.warning('  CR2toFITSg failed!')
        sys.exit(1)
    image.tempFiles.append(image.workingFile)
    image.fileExt = os.path.splitext(image.workingFile)[1]
    
    image.logger.info("Reading info file created by skycam.c")
    ReadSkycamInfo(RawFile, image.workingFile)
    image.GetHeader()           ## Extract values from header

    image.logger.info("Creating full frame jpeg symlink to {}".format(skycamJPEGfile))
    image.jpegFileNames = [FullFrameJPEG]
    if not os.path.exists(os.path.join(config.pathPlots, FullFrameJPEG)):
        image.logger.info("Creating symlink to skycam.c jpeg.")
        os.symlink(skycamJPEGfile, os.path.join(config.pathPlots, FullFrameJPEG))

    image.SolveAstrometry()         ## Solve Astrometry
    image.GetHeader()               ## Extract values from header
    image.DeterminePointingError()  ## Calculate Pointing Error
    image.Crop()                    ## Crop Image
    image.GetHeader()               ## Extract values from header
    image.RunSExtractor()           ## Run SExtractor
    image.DetermineFWHM()           ## Determine FWHM from SExtractor results
    image.MakeJPEG(CropFrameJPEG, markDetectedStars=False, markPointing=True, binning=1)
    image.CleanUp()                 ## Cleanup (delete) temporary files.
    image.CalculateProcessTime()    ## Calculate how long it took to process this image
    fields=["Date and Time", "Filename", "Target", "ExpTime", "Alt", "Az", "Airmass", "MoonSep", "MoonIllum", "FWHM", "ellipticity", "Background", "PErr", "PosAng", "nStars", "ProcessTime"]
    image.AddWebLogEntry(htmlImageList, fields=fields) ## Add line for this image to HTML table
    image.AddSummaryEntry(summaryFile)  ## Add line for this image to text table
    

if __name__ == '__main__':
    main()
