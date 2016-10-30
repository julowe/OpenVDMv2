# =================================================================================== #
#
#         FILE:  hpr_parser.py
#
#        USAGE:  hpr_parser.py [-h] <dataFile>
#
#  DESCRIPTION:  Parse the supplied NMEA-formtted HPR file (w/ SCS formatted timestamp)
#                and return the json-formatted string used by OpenVDM as part of it's
#                Data dashboard. 
#
#      OPTIONS:  [-h] Return the help message.
#                <dataFile> Full or relative path of the data file to process.
#
# REQUIREMENTS:  python2.7, Python Modules: sys, os, argparse, json, pandas
#
#         BUGS:
#        NOTES:
#       AUTHOR:  Webb Pinner
#      COMPANY:  Capable Solutions
#      VERSION:  1.0
#      CREATED:  2016-08-29
#     REVISION:  
#
# LICENSE INFO:  Open Vessel Data Management v2.1 (OpenVDMv2)
#                Copyright (C) 2016 OceanDataRat.org
#
#    This program is free software: you can redistribute it and/or modify it under the
#    terms of the GNU General Public License as published by the Free Software
#    Foundation, either version 3 of the License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful, but WITHOUT ANY
#    WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
#    PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License #    along with
#    this program.  If not, see <http://www.gnu.org/licenses/>.
#
# =================================================================================== #
from __future__ import print_function
import pandas as pd
import json
import argparse
import subprocess
import tempfile
import sys
import copy
import os
import shutil
import csv
from itertools import (takewhile,repeat)

#	visualizerDataObj = {'data':[], 'unit':'', 'label':''}
#	statObj = {'statName':'', 'statUnit':'', 'statType':'', 'statData':[]}
#	qualityTestObj = {"testName": "", "results": ""}

RAW_COLUMNS = ['date','time','hdr','heading','pitch', 'roll', 'checksum']
PROC_COLUMNS = ['date_time','heading','pitch', 'roll']
CROP_COLUMNS = ['date_time','heading','pitch', 'roll']

MIN_HEADING = 0
MAX_HEADING = 360

MIN_PITCH = -45
MAX_PITCH = 45

MIN_ROLL = -45
MAX_ROLL = 45

MAX_DELTA_T = pd.Timedelta('10 seconds')

RESAMPLE_INTERVAL = '1T' # 1 minute

DEBUG = False

def debugPrint(*args, **kwargs):
	if DEBUG:
		errPrint(*args, **kwargs)

def errPrint(*args, **kwargs):
	    print(*args, file=sys.stderr, **kwargs)

def rawincount(filename):
	f = open(filename, 'rb')
	bufgen = takewhile(lambda x: x, (f.read(1024*1024) for _ in repeat(None)))
	return sum( buf.count(b'\n') for buf in bufgen )

def csvCleanup(filepath):

	command = ['csvclean', filepath]
	errors = 0
	
	s = ' '
	debugPrint(s.join(command))
	
	proc = subprocess.Popen(command,stderr=subprocess.PIPE, stdout=subprocess.PIPE)
	out, err = proc.communicate()

	(dirname, basename) = os.path.split(filepath)
	debugPrint("Dirname:" + dirname)
	debugPrint("Basename:" + basename)

	outfile = os.path.join(dirname, os.path.splitext(basename)[0] + '_out.csv')
	errfile = os.path.join(dirname, os.path.splitext(basename)[0] + '_err.csv')
	
	debugPrint("Outfile: " + outfile)
	debugPrint("Errfile: " + errfile)
	if os.path.isfile(errfile):
		errors = rawincount(errfile)-1

	return (errors, outfile)

	debugPrint("Errors: " + errors)

def parseFile(filePath):
	output = {}
	output['visualizerData'] = []
	output['qualityTests'] = []
	output['stats'] = []

	tmpdir = tempfile.mkdtemp()
	shutil.copy(filePath, tmpdir)
	(errors, outfile) = csvCleanup(os.path.join(tmpdir, os.path.basename(filePath)))

	rawIntoDf = {'date_time':[],'heading':[], 'pitch':[], 'roll':[]}

	csvfile = open(outfile, 'r')
	reader = csv.DictReader( csvfile, RAW_COLUMNS)

	for line in reader:
		
		try:

			line_date_time = line['date'] + ' ' + line['time']

			line_heading = float(line['heading'])
			line_pitch = float(line['pitch'])
			line_roll = float(line['roll'].split('*')[0])
		except:

			debugPrint('Parsing error: ',line)
			errors += 1

		else:

			if line_heading > MAX_HEADING or line_heading < MIN_HEADING:
				errors += 1
				continue

			rawIntoDf['date_time'].append(line_date_time)
			rawIntoDf['heading'].append(line_heading)
			rawIntoDf['pitch'].append(line_pitch)
			rawIntoDf['roll'].append(line_roll)

	shutil.rmtree(tmpdir)

	if len(rawIntoDf['date_time']) == 0:
		return None

	df_proc = pd.DataFrame(rawIntoDf)

	df_proc['date_time'] = pd.to_datetime(df_proc['date_time'], infer_datetime_format=True)

	df_proc = df_proc.join(df_proc['date_time'].diff().to_frame(name='deltaT'))

	rowValidityStat = {'statName':'Row Validity', 'statType':'rowValidity', 'statData':[len(df_proc), errors]}
	output['stats'].append(rowValidityStat)

	headingStat = {'statName': 'Heading Bounds','statUnit': 'deg', 'statType':'bounds', 'statData':[round(df_proc['heading'].min(),3), round(df_proc['heading'].max(),3)]}
	output['stats'].append(headingStat)

	#headingValidityStat = {'statName':'Heading Validity', 'statType':'valueValidity', 'statData':[len(df_proc[(df_proc['heading'] >= MIN_HEADING) & (df_proc['heading'] <= MAX_HEADING)]),len(df_proc[(df_proc['heading'] < MIN_HEADING) & (df_proc['heading'] > MAX_HEADING)])]}
	#output['stats'].append(headingValidityStat)

	pitchStat = {'statName': 'Pitch Bounds','statUnit': 'deg', 'statType':'bounds', 'statData':[round(df_proc['pitch'].min(),3), round(df_proc['pitch'].max(),3)]}
	output['stats'].append(pitchStat)

	pitchValidityStat = {'statName':'Pitch Validity', 'statType':'valueValidity', 'statData':[len(df_proc[(df_proc['pitch'] >= MIN_PITCH) & (df_proc['pitch'] <= MAX_PITCH)]),len(df_proc[(df_proc['pitch'] < MIN_PITCH) & (df_proc['pitch'] > MAX_PITCH)])]}
	output['stats'].append(pitchValidityStat)

	rollStat = {'statName': 'Roll Bounds','statUnit': 'deg', 'statType':'bounds', 'statData':[round(df_proc['roll'].min(),3), round(df_proc['roll'].max(),3)]}
	output['stats'].append(rollStat)

	rollValidityStat = {'statName':'Roll Validity', 'statType':'valueValidity', 'statData':[len(df_proc[(df_proc['roll'] >= MIN_ROLL) & (df_proc['roll'] <= MAX_ROLL)]),len(df_proc[(df_proc['roll'] < MIN_ROLL) & (df_proc['roll'] > MAX_ROLL)])]}
	output['stats'].append(rollValidityStat)

	temporalStat = {'statName': 'Temporal Bounds','statUnit': 'seconds', 'statType':'timeBounds', 'statData':[df_proc.date_time.min().strftime('%s'), df_proc.date_time.max().strftime('%s')]}
	output['stats'].append(temporalStat)

	deltaTStat = {"statName": "Delta-T Bounds","statUnit": "seconds","statType": "bounds","statData": [round(df_proc.deltaT.min().total_seconds(),3), round(df_proc.deltaT.max().total_seconds(),3)]}
	output['stats'].append(deltaTStat)

	deltaTValidityStat = {'statName':'Temporal Validity', 'statType':'valueValidity', 'statData':[len(df_proc[(df_proc['deltaT'] <= MAX_DELTA_T)]),len(df_proc[(df_proc['deltaT'] > MAX_DELTA_T)])]}
	output['stats'].append(deltaTValidityStat)

	rowQualityTest = {"testName": "Rows", "results": "Passed"}
	if rowValidityStat['statData'][1] > 0:
		if rowValidityStat['statData'][1]/rowValidityStat['statData'][0] > .10:
			rowQualityTest['results'] = "Failed"
		else:
			rowQualityTest['results'] = "Warning"
	output['qualityTests'].append(rowQualityTest)

	deltaTQualityTest = {"testName": "DeltaT", "results": "Passed"}
	if deltaTValidityStat['statData'][1] > 0:
		if deltaTValidityStat['statData'][1]/len(df_proc) > .10:
			deltaTQualityTest['results'] = "Failed"
		else:
			deltaTQualityTest['results'] = "Warning"
	output['qualityTests'].append(deltaTQualityTest)

	#headingQualityTest = {"testName": "Heading", "results": "Passed"}
	#if headingValidityStat['statData'][1] > 0:
	#	if headingValidityStat['statData'][1]/len(df_proc) > .10:
	#		headingQualityTest['results'] = "Failed"
	#	else:
	#		headingQualityTest['results'] = "Warning"
	#output['qualityTests'].append(headingQualityTest)

	pitchQualityTest = {"testName": "Pitch", "results": "Passed"}
	if pitchValidityStat['statData'][1] > 0:
		if pitchValidityStat['statData'][1]/len(df_proc) > .10:
			pitchQualityTest['results'] = "Failed"
		else:
			pitchQualityTest['results'] = "Warning"
	output['qualityTests'].append(pitchQualityTest)

	rollQualityTest = {"testName": "Roll", "results": "Passed"}
	if rollValidityStat['statData'][1] > 0:
		if rollValidityStat['statData'][1]/len(df_proc) > .10:
			rollQualityTest['results'] = "Failed"
		else:
			rollQualityTest['results'] = "Warning"
	output['qualityTests'].append(rollQualityTest)

	df_crop = df_proc[CROP_COLUMNS]

	df_crop = df_crop.set_index('date_time')

	df_crop = df_crop.resample(RESAMPLE_INTERVAL, label='right', closed='right').mean()

	df_crop = df_crop.reset_index()

	decimals = pd.Series([3, 3, 3], index=['heading', 'pitch', 'roll'])
	df_crop = df_crop.round(decimals)

	visualizerDataObj = {'data':[], 'unit':'', 'label':''}
	visualizerDataObj['data'] = json.loads(df_crop[['date_time','heading']].to_json(orient='values'))
	visualizerDataObj['unit'] = 'deg'
	visualizerDataObj['label'] = 'Heading'
	output['visualizerData'].append(copy.deepcopy(visualizerDataObj))

	visualizerDataObj['data'] = json.loads(df_crop[['date_time','pitch']].to_json(orient='values'))
	visualizerDataObj['unit'] = 'deg, bow up +'
	visualizerDataObj['label'] = 'Pitch'
	output['visualizerData'].append(copy.deepcopy(visualizerDataObj))
	
	visualizerDataObj['data'] = json.loads(df_crop[['date_time','roll']].to_json(orient='values'))
	visualizerDataObj['unit'] = 'deg, starboard +'
	visualizerDataObj['label'] = 'Roll'
	output['visualizerData'].append(copy.deepcopy(visualizerDataObj))

	return output

# -------------------------------------------------------------------------------------
# Main function of the script should it be run as a stand-alone utility.
# -------------------------------------------------------------------------------------
def main(argv):

	parser = argparse.ArgumentParser(description='Parse NMEA HPR data')
	parser.add_argument('dataFile', metavar='dataFile', help='the raw data file to process')
	parser.add_argument('-d', '--debug', action='store_true', help=' display debug messages')

	args = parser.parse_args()
	if args.debug:
		global DEBUG
		DEBUG = True
		debugPrint("Running in debug mode")

	if not os.path.isfile(args.dataFile):
		errPrint('ERROR: File not found\n')
		sys.exit(1)

	jsonObj = parseFile(args.dataFile)
	if jsonObj:
		print(json.dumps(jsonObj))
		sys.exit(0)
	else:
		sys.exit(1)
            
# -------------------------------------------------------------------------------------
# Required python code for running the script as a stand-alone utility
# -------------------------------------------------------------------------------------
if __name__ == "__main__":
    main(sys.argv[1:])
