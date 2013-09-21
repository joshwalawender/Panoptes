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

import ephem
import astropy.units as u

import IQMon


class ParseError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


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
    RawBasename, RawExt = os.path.splitext(FitsFilename)


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
    tel.pixelSize = 5.0*u.micron     ## Need to determine correct pixel size
    tel.aperture = 60.7.*u.mm
    tel.gain = 1.6 / u.adu           ## Need to determine correct gain
    tel.unitsForFWHM = 1.*u.pix
    tel.ROI = "[1024:3072,1024:3072]"
    tel.thresholdFWHM = 4.0*u.pix
    tel.thresholdPointingErr = 10.0*u.arcmin
    tel.thresholdEllipticity = 0.30*u.dimensionless_unscaled
    tel.pixelScale = tel.pixelSize.to(u.mm)/tel.focalLength.to(u.mm)*u.radian.to(u.arcsec)*u.arcsec/u.pix
    tel.fRatio = tel.focalLength.to(u.mm)/tel.aperture.to(u.mm)
    tel.SExtractorPhotAperture = 6.0*u.pix
    tel.SExtractorSeeing = 2.0*u.arcsec
    tel.SExtractorSaturation = 30000.*u.adu  ## Need to determine correct gain
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
    IQMonLogFileName = os.path.join(config.pathLog, tel.longName, DataNightString+"_"+tel.name+"_IQMonLog.txt")
    htmlImageList = os.path.join(config.pathLog, tel.longName, DataNightString+"_"+tel.name+".html")
    summaryFile = os.path.join(config.pathLog, tel.longName, DataNightString+"_"+tel.name+"_Summary.txt")
    FullFrameJPEG = image.rawFileBasename+"_full.jpg"
    CropFrameJPEG = image.rawFileBasename+"_crop.jpg"
    BackgroundJPEG = image.rawFileBasename+"_bkgnd.jpg"
    if args.clobber:
        if os.path.exists(IQMonLogFileName): os.remove(IQMonLogFileName)
        if os.path.exists(htmlImageList): os.remove(htmlImageList)
        if os.path.exists(summaryFile): os.remove(summaryFile)

    ##-------------------------------------------------------------------------
    ## Perform Actual Image Analysis
    ##-------------------------------------------------------------------------
    image.MakeLogger(IQMonLogFileName, args.verbose)
    image.logger.info("###### Processing Image:  %s ######", FitsFilename)
    image.logger.info("Setting telescope variable to %s", telescope)
    image.ReadImage()           ## Create working copy of image (don't edit raw file!)
    image.GetHeader()           ## Extract values from header
    image.MakeJPEG(FullFrameJPEG, rotate=True, markPointing=True, binning=4)
    if not image.imageWCS:      ## If no WCS found in header ...
        image.SolveAstrometry() ## Solve Astrometry
        image.GetHeader()       ## Refresh Header
    image.DeterminePointingError()            ## Calculate Pointing Error
    darks = ListDarks(image)    ## List dark files
    if darks and len(darks) > 0:
        image.DarkSubtract(darks)   ## Dark Subtract Image
    image.Crop()                ## Crop Image
    image.GetHeader()           ## Refresh Header
    image.RunSExtractor()       ## Run SExtractor
    image.DetermineFWHM()       ## Determine FWHM from SExtractor results
    image.MakeJPEG(CropFrameJPEG, markStars=True, markPointing=True, rotate=True, binning=1)
#     image.MakeJPEG(BackgroundJPEG, markStars=True, markPointing=False, rotate=True, binning=1, backgroundSubtracted=True)
    image.CleanUp()             ## Cleanup (delete) temporary files.
    image.CalculateProcessTime()## Calculate how long it took to process this image
    image.AddWebLogEntry(htmlImageList) ## Add line for this image to HTML table
    image.AddSummaryEntry(summaryFile)  ## Add line for this image to text table
    

if __name__ == '__main__':
    main()
