#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging
import re
import numpy as np
import subprocess
import netpbmfile
import astropy.io.fits as fits

##-------------------------------------------------------------------------
## Main Program
##-------------------------------------------------------------------------
def main():

    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = argparse.ArgumentParser(
             description="Program description.")
    ## add flags
    parser.add_argument("-v", "--verbose",
        action="store_true", dest="verbose",
        default=False, help="Be verbose! (default = False)")
    ## add arguments
    parser.add_argument("input",
        type=str,
        help="The input CR2 file")
    parser.add_argument("-o", "--output",
        type=str, dest="output",
        help="The output fits file.")
    args = parser.parse_args()


    ##-------------------------------------------------------------------------
    ## Create logger object
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('MyLogger')
    logger.setLevel(logging.DEBUG)
    ## Set up console output
    LogConsoleHandler = logging.StreamHandler()
    if args.verbose:
        LogConsoleHandler.setLevel(logging.DEBUG)
    else:
        LogConsoleHandler.setLevel(logging.INFO)
    LogFormat = logging.Formatter('%(levelname)8s: %(message)s')
    LogConsoleHandler.setFormatter(LogFormat)
    logger.addHandler(LogConsoleHandler)
    ## Set up file output
#     LogFileName = None
#     LogFileHandler = logging.FileHandler(LogFileName)
#     LogFileHandler.setLevel(logging.DEBUG)
#     LogFileHandler.setFormatter(LogFormat)
#     logger.addHandler(LogFileHandler)

    ##-------------------------------------------------------------------------
    ## 
    ##-------------------------------------------------------------------------
    ## Check the input has cr2 extension
    inputBasename, inputExt = os.path.splitext(args.input)
    if not re.match("\.cr2", inputExt, flags=re.I):
        logger.critical("Input file {0} does not appear to have CR2 extension.".format(args.input))
        sys.exit()
    ## If no output file specified
    if not args.output:
        args.output = args.input.replace(inputExt, ".fits")
    ## Check the output has fits extension
    outputBasename, outputExt = os.path.splitext(args.output)
    if not re.match("\.fi?ts", outputExt, flags=re.I):
        logger.critical("Output file {0} does not appear to have fits extension.".format(args.output))
        sys.exit()

    ## Use dcraw to get header information
    dcrawGetInfoCommand = ["dcraw", "-i", "-v", args.input]
    logger.info("Calling dcraw using: {0}".format(repr(dcrawGetInfoCommand)))
    try:
        dcrawInfo = subprocess.check_output(dcrawGetInfoCommand)
    except:
        logger.error("Could not get dcraw info from file.")

    for line in dcrawInfo.split("\n"):
        logger.debug(line)
        
    ## Use dcraw to convert cr2 to ppm
    ppmfile = args.input.replace(inputExt, ".ppm")
    if not os.path.exists(ppmfile):
        dcrawCommand = "dcraw -4 -c "+args.input+" > "+ppmfile
        logger.info("Calling dcraw using: {0}".format(dcrawCommand))
        try:
            os.system(dcrawCommand)
        except:
            logger.critical("dcraw failed")
    else:
        logger.info("PPM file already exists, using that file.")

    logger.info("Reading PPM file.")
    im = netpbmfile.NetpbmFile(ppmfile).asarray()
    
    logger.info("Writing new fits file: {0}".format(args.output))
    if os.path.exists(args.output): os.remove(args.output)
    phdu = fits.PrimaryHDU()
    redhdu = fits.ImageHDU(im[:,:,0])
    greenhdu = fits.ImageHDU(im[:,:,1])
    bluehdu = fits.ImageHDU(im[:,:,2])
    hdulist = fits.HDUList([phdu, redhdu, greenhdu, bluehdu])
    hdulist.writeto(args.output)
    


#     hdu = fits.PrimaryHDU(green)
#     hdu.writeto('GreenChannel.fits')

if __name__ == '__main__':
    main()
