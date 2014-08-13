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
    ## Create Telescope Object
    ##-------------------------------------------------------------------------
    path_temp = '/home/joshw/IQMon/tmp'
    path_plots = '/home/joshw/IQMon/Plots'
    tel = IQMon.Telescope(path_temp, path_plots)
    tel.name = "Panoptes"
    tel.long_name = "Panoptes"
    tel.focal_length = 85.*u.mm
    tel.pixel_size = 4.6*u.micron     ## Need to determine correct pixel size
    tel.aperture = 60.7*u.mm
    tel.gain = 1.6 / u.adu           ## Need to determine correct gain
    tel.units_for_FWHM = 1.*u.pix
    tel.ROI = None
    tel.threshold_FWHM = 3.0*u.pix
    tel.threshold_pointing_err = 60.0*u.arcmin
    tel.threshold_ellipticity = 0.30*u.dimensionless_unscaled
    tel.pixel_scale = tel.pixel_size.to(u.mm)/tel.focal_length.to(u.mm)*u.radian.to(u.arcsec)*u.arcsec/u.pix
    tel.fRatio = tel.focal_length.to(u.mm)/tel.aperture.to(u.mm)
    tel.SExtractor_params = {
                            'DETECT_THRESH': 6.0,
                            'ANALYSIS_THRESH': 6.0,
                            'PHOT_APERTURES': 6.0,
                            'SEEING': 3.5,
                            'SATUR_LEVEL': 30000.,
                            'FILTER': 'N',
                            }
    tel.distortionOrder = 5
    tel.pointing_marker_size = 15*u.arcmin
    ## Define Site (ephem site object)
    tel.site = ephem.Observer()
    tel.check_units()
    tel.define_pixel_scale()

    ##-------------------------------------------------------------------------
    ## Create IQMon.Image Object
    ##-------------------------------------------------------------------------
    image = IQMon.Image(args.filename, tel=tel)  ## Create image object

    ##-------------------------------------------------------------------------
    ## Create Filenames
    ##-------------------------------------------------------------------------
    path_log = os.path.join(os.path.expanduser('~'), 'IQMon', 'Logs')
    path_plots = os.path.join(os.path.expanduser('~'), 'IQMon', 'Plots')
    IQMonLogFileName = os.path.join(path_log, DataNightString+"_"+tel.name+"_IQMonLog.txt")
    htmlImageList = os.path.join(path_log, DataNightString+"_"+tel.name+".html")
    summaryFile = os.path.join(path_log, DataNightString+"_"+tel.name+"_Summary.txt")

    if not os.path.exists(os.path.join(path_plots, DataNightString)):
        os.mkdir(os.path.join(path_plots, DataNightString))
    if args.clobber:
        if os.path.exists(IQMonLogFileName): os.remove(IQMonLogFileName)
        if os.path.exists(htmlImageList): os.remove(htmlImageList)
        if os.path.exists(summaryFile): os.remove(summaryFile)


    ##-------------------------------------------------------------------------
    ## Perform Actual Image Analysis
    ##-------------------------------------------------------------------------
    image.make_logger(IQMonLogFileName, args.verbose)
    image.logger.info("###### Processing Image:  %s ######", args.filename)
    image.read_image()
    image.logger.info("Reading info file created by skycam.c")
    ReadSkycamInfo(RawFile, image.working_file)
    image.read_header()

    FullFrameJPEG = os.path.join(DataNightDirectory, DataNightString, 'JPEG', '{}.jpeg'.format(RawFilename))
    FullFrameSymLink = os.path.join(path_plots, DataNightString, '{}.jpg'.format(RawBasename))
    image.logger.info("Creating full frame jpeg symlink to {}".format(FullFrameJPEG))
    if os.path.exists(FullFrameJPEG) and not os.path.exists(FullFrameSymLink):
        image.logger.info("Creating symlink to skycam.c jpeg.")
        os.symlink(FullFrameJPEG, FullFrameSymLink)
    image.jpeg_file_names = [os.path.join(DataNightString, '{}.jpg'.format(RawBasename))]

    if not image.image_WCS:      ## If no WCS found in header ...
        image.solve_astrometry() ## Solve Astrometry
        image.read_header()       ## Refresh Header

    image.determine_pointing_error()  ## Calculate Pointing Error
    image.run_SExtractor()           ## Run SExtractor

#     image.run_SCAMP(catalog='UCAC-3')
#     image.run_SWarp()
#     image.read_header()           ## Extract values from header
#     image.get_local_UCAC4(local_UCAC_command="/Users/joshw/Data/UCAC4/access/u4test", local_UCAC_data="/Users/joshw/Data/UCAC4/u4b")
#     image.run_SExtractor(assoc=True)

    image.determine_FWHM()       ## Determine FWHM from SExtractor results
    image.make_PSF_plot()

    cropped_JPEG = image.raw_file_basename+"_crop.jpg"
    image.new_make_JPEG(cropped_JPEG,\
                        mark_pointing=True,\
                        mark_detected_stars=False,\
                        mark_catalog_stars=False,\
                        crop=(int(image.nXPix/2)-1024, int(image.nYPix/2)-1024, int(image.nXPix/2)+1024, int(image.nYPix/2)+1024),
                        transform='flip_vertical')

    image.clean_up()                 ## Cleanup (delete) temporary files.
    image.calculate_process_time()    ## Calculate how long it took to process this image
    fields=["Date and Time", "Filename", "Target", "ExpTime", "Alt", "Az", "Airmass", "MoonSep", "MoonIllum", "FWHM", "ellipticity", "Background", "PErr", "PosAng", "nStars", "ProcessTime"]
    image.add_web_log_entry(htmlImageList, fields=fields) ## Add line for this image to HTML table
    image.add_summary_entry(summaryFile)  ## Add line for this image to text table
    

if __name__ == '__main__':
    main()
