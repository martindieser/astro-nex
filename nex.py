#!/usr/bin/python
from optparse import OptionParser
parser = OptionParser()

parser.add_option("-c", "--console", action="store_true", default=False)
(options, args) = parser.parse_args()

from path import Path
appath = Path.cwd() 
from astronex import nex
nex.main(appath,options.console)
