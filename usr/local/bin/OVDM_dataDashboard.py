# ----------------------------------------------------------------------------------- #
#
#         FILE:  OVDM_dataDashboard.py
#
#  DESCRIPTION:  Gearman worker tha handles the creation and update of OVDM data
#                dashboard objects.
#
#         BUGS:
#        NOTES:
#       AUTHOR:  Webb Pinner
#      COMPANY:  Capable Solutions
#      VERSION:  2.2
#      CREATED:  2015-01-01
#     REVISION:  2016-10-19
#
# LICENSE INFO: Open Vessel Data Management (OpenVDM) Copyright (C) 2016  Webb Pinner
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/gpl-3.0.html>.
#
# ----------------------------------------------------------------------------------- #
from __future__ import print_function
import argparse
import os
import sys
import gearman
import shutil
import errno
import json
import argparse
import signal
import pwd
import grp
import time
import subprocess
import openvdm

customTaskLookup = [
    {
        "taskID": "0",
        "name": "updateDataDashboard",
        "longName": "Updating Data Dashboard",
    }
]

DEBUG = False
new_worker = None

dataDashboardManifestFN = 'manifest.json'

def debugPrint(*args, **kwargs):
    global DEBUG
    if DEBUG:
        errPrint(*args, **kwargs)


def errPrint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def build_filelist(sourceDir):

    returnFiles = []
    for root, dirnames, filenames in os.walk(sourceDir):
        for filename in filenames:
            returnFiles.append(os.path.join(root, filename))

    returnFiles = [filename.replace(sourceDir + '/', '', 1) for filename in returnFiles]
    return returnFiles


def build_dashboardData_filelist(worker):
    baseDir = worker.shipboardDataWarehouseConfig['shipboardDataWarehouseBaseDir']
    cruiseDir = os.path.join(baseDir, worker.cruiseID)
    dataDashboardDir = os.path.join(cruiseDir, worker.OVDM.getRequiredExtraDirectoryByName('Dashboard Data')['destDir'])

    returnFiles = []
    for root, dirnames, filenames in os.walk(dataDashboardDir):
        for filename in filenames:
            returnFiles.append(os.path.join(root, filename))

    returnFiles = [filename.replace(cruiseDir + '/', '', 1) for filename in returnFiles]
    return returnFiles


def setOwnerGroupPermissions(worker, path):

    warehouseUser = worker.shipboardDataWarehouseConfig['shipboardDataWarehouseUsername']

    #debugPrint(path)

    uid = pwd.getpwnam(warehouseUser).pw_uid
    gid = grp.getgrnam(warehouseUser).gr_gid
    # Set the file permission and ownership for the current directory

    
    if os.path.isfile(path):
        try:
            debugPrint("Setting ownership for", path, "to", warehouseUser + ":" + warehouseUser)
            os.chown(path, uid, gid)
            os.chmod(path, 0755)
        except OSError:
            errPrint("Unable to set file permissions for", path)
            return False
    elif os.path.isdir(path):

        for item in os.listdir(path):
            itempath = os.path.join(path, item)
            if os.path.isdir(itempath):
                try:
                    if not setOwnerGroupPermissions(worker, itempath):
                        return False
                except OSError:
                    return False
            elif os.path.isfile(itempath):
                try:
                    debugPrint("Setting ownership for", itempath, "to", warehouseUser + ":" + warehouseUser)
                    os.chown(itempath, uid, gid)
                    os.chmod(itempath, 0644)
                except OSError:
                    errPrint("Unable to set file permissions for", itempath)
                    return False
    return True


def output_JSONDataToFile(worker, filePath, contents):
    
    try:
        os.makedirs(os.path.dirname(filePath))
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
            worker.stopJob()
            errPrint("Unable to create parent directory for data file")
            return False
#    finally:
#        setOwnerGroupPermissions(worker, os.path.dirname(filePath))
    
    try:
        #print "Open JSON file"
        JSONFile = open(filePath, 'w')

        debugPrint("Saving JSON file:", filePath)
        json.dump(contents, JSONFile)

    except IOError:
        errPrint("Error Saving JSON file:", filePath)
        return False

    finally:
        JSONFile.close()

    return True


class OVDMGearmanWorker(gearman.GearmanWorker):

    def __init__(self, host_list=None):
        self.stop = False
        self.quit = False
        self.OVDM = openvdm.OpenVDM()
        self.cruiseID = ''
        self.shipboardDataWarehouseConfig = {}
        self.task = None
        super(OVDMGearmanWorker, self).__init__(host_list=[self.OVDM.getGearmanServer()])

    def get_task(self, current_job):
        tasks = self.OVDM.getTasks()
        for task in tasks:
            if task['name'] == current_job.task:
                self.task = task
                return True
        
        for task in customTaskLookup:
            if task['name'] == current_job.task:
                self.task = task
                return True

        self.task = None
        return False


    def on_job_execute(self, current_job):
        self.get_task(current_job)
        payloadObj = json.loads(current_job.data)
        self.shipboardDataWarehouseConfig = self.OVDM.getShipboardDataWarehouseConfig()

        self.cruiseID = self.OVDM.getCruiseID()
        if len(payloadObj) > 0:
            try:
                payloadObj['cruiseID']
            except KeyError:
                self.cruiseID = self.OVDM.getCruiseID()
            else:
                self.cruiseID = payloadObj['cruiseID']

        if int(self.task['taskID']) > 0:

            self.OVDM.setRunning_task(self.task['taskID'], os.getpid(), current_job.handle)
        else:
            self.OVDM.trackGearmanJob(self.task['longName'], os.getpid(), current_job.handle)

        errPrint("Job:", current_job.handle + ",", self.task['longName'], "started at:  ", time.strftime("%D %T", time.gmtime()))
        
        return super(OVDMGearmanWorker, self).on_job_execute(current_job)


    def on_job_exception(self, current_job, exc_info):
        errPrint("Job:", current_job.handle + ",", self.task['longName'], "failed at:   ", time.strftime("%D %T", time.gmtime()))
        
        self.send_job_data(current_job, json.dumps([{"partName": "Worker crashed", "result": "Fail"}]))
        if int(self.task['taskID']) > 0:
            self.OVDM.setError_task(self.task['taskID'], "Worker crashed")
        else:
            self.OVDM.sendMsg(self.task['longName'] + ' failed', 'Worker crashed')
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        errPrint(exc_type, fname, exc_tb.tb_lineno)
        return super(OVDMGearmanWorker, self).on_job_exception(current_job, exc_info)


    def on_job_complete(self, current_job, job_results):
        resultsObj = json.loads(job_results)

        debugPrint("Preparing subsequent Gearman jobs")
        gm_client = gearman.GearmanClient([self.OVDM.getGearmanServer()])

        jobData = {}
        jobData['cruiseID'] = self.cruiseID
        jobData['files'] = resultsObj['files']

        if current_job.task == 'updateDataDashboard':

            payloadObj = json.loads(current_job.data)
            jobData['collectionSystemTransferID'] = payloadObj['collectionSystemTransferID']

            for task in self.OVDM.getTasksForHook(current_job.task):
                debugPrint("Adding task:", task)
                submitted_job_request = gm_client.submit_job(task, json.dumps(jobData), background=True)

        elif current_job.task == 'rebuildDataDashboard':
            for task in self.OVDM.getTasksForHook(current_job.task):
                debugPrint("Adding task:", task)
                submitted_job_request = gm_client.submit_job(task, json.dumps(jobData), background=True)

        if len(resultsObj['parts']) > 0:
            if resultsObj['parts'][-1]['result'] == "Fail": # Final Verdict
                if int(self.task['taskID']) > 0:
                    self.OVDM.setError_task(self.task['taskID'], resultsObj['parts'][-1]['partName'])
                else:
                    self.OVDM.sendMsg(self.task['longName'] + ' failed', resultsObj['parts'][-1]['partName'])
            else:
                if int(self.task['taskID']) > 0:
                    self.OVDM.setIdle_task(self.task['taskID'])
        else:
            if int(self.task['taskID']) > 0:
                self.OVDM.setIdle_task(self.task['taskID'])
        
        debugPrint('Job Results:', json.dumps(resultsObj, indent=2))
            
        errPrint("Job:", current_job.handle + ",", self.task['longName'], "completed at:", time.strftime("%D %T", time.gmtime()))
            
        return super(OVDMGearmanWorker, self).send_job_complete(current_job, job_results)

    def after_poll(self, any_activity):
        self.stop = False
        self.taskID = '0'
        if self.quit:
            errPrint("Quitting")
            self.shutdown()
        else:
            self.quit = False
        return True


    def stopTask(self):
        self.stop = True
        debugPrint("Stopping current task...")


    def quitWorker(self):
        self.stop = True
        self.quit = True
        debugPrint("Quitting worker...")


def task_updateDataDashboard(worker, job):

    job_results = {
        'parts':[],
        'files':{
            'new':[],
            'updated':[]
        }
    }

    payloadObj = json.loads(job.data)
    debugPrint('Payload:', json.dumps(payloadObj, indent=2))

    baseDir = worker.shipboardDataWarehouseConfig['shipboardDataWarehouseBaseDir']
    cruiseDir = os.path.join(baseDir, worker.cruiseID)
    dataDashboardDir = os.path.join(cruiseDir, worker.OVDM.getRequiredExtraDirectoryByName('Dashboard Data')['destDir'])
    dataDashboardManifestFilePath = os.path.join(dataDashboardDir, dataDashboardManifestFN)
    collectionSystemTransfer = worker.OVDM.getCollectionSystemTransfer(payloadObj['collectionSystemTransferID'])

    worker.send_job_status(job, 5, 100)

    debugPrint('Collection System Transfer:', collectionSystemTransfer['name'])

    newManifestEntries = []
    removeManifestEntries = []

    #check for processing file
    processingScriptFilename = os.path.join(worker.OVDM.getDashboardDataProcessingScriptDir(), collectionSystemTransfer['name'].replace(' ','') + worker.OVDM.getDashboardDataProcessingScriptSuffix())
    debugPrint("Processing Script Filename: " + processingScriptFilename)

    if os.path.isfile(processingScriptFilename):
        job_results['parts'].append({"partName": "Dashboard Processing File Located", "result": "Pass"})
    else:
        debugPrint("Processing script not found")
        #job_results['parts'].append({"partName": "Dashboard Processing File Located", "result": "Fail"})
        return json.dumps(job_results)

    worker.send_job_status(job, 10, 100)

    #build filelist
    fileList = []

    if payloadObj['files']['new'] or payloadObj['files']['updated']:
        fileList = payloadObj['files']['new']
        fileList += payloadObj['files']['updated']
        debugPrint('File List:', json.dumps(fileList, indent=2))
        job_results['parts'].append({"partName": "Retrieve Filelist", "result": "Pass"})

    else:
        debugPrint("No new or updated files to process")
        job_results['parts'].append({"partName": "Retrieve Filelist", "result": "Pass"})
        return json.dumps(job_results)

    fileCount = len(fileList)
    index = 0
    for filename in fileList:
        
        if worker.stop:
            break

        debugPrint("Processing file:", filename)
        jsonFileName = filename.split('.')[0] + '.json'
        rawFilePath = os.path.join(cruiseDir, filename)
        jsonFilePath = os.path.join(dataDashboardDir, jsonFileName)

        if os.stat(rawFilePath).st_size == 0:
            debugPrint("File is empty")
            continue

        command = ['python', processingScriptFilename, '--dataType', rawFilePath]

        s = ' '
        debugPrint(s.join(command))

        proc = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        out, err = proc.communicate()

        if out:
            dd_type = out.rstrip('\n')
            debugPrint("Found to be type:", dd_type)

            command = ['python', processingScriptFilename, rawFilePath]

            s = ' '
            debugPrint(s.join(command))

            proc = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            out, err = proc.communicate()

            if out:
                try:
                    debugPrint("Verifying output")
                    outObj = json.loads(out)
                except:
                    errPrint("Error parsing JSON output from file", filename)
                    job_results['parts'].append({"partName": "Parsing JSON output from file " + filename, "result": "Fail"})
                    continue
                else:
                    if 'error' in outObj:
                        errorTitle = 'Datafile Parsing error'
                        errorBody = outObj['error']
                        errPrint(errorTitle + ': ', errorBody)
                        worker.OVDM.sendMsg(errorTitle,errorBody)
                    else:
                        if output_JSONDataToFile(worker, jsonFilePath, outObj):
                            job_results['parts'].append({"partName": "Writing DashboardData file: " + filename, "result": "Pass"})
                            if(setOwnerGroupPermissions(worker, jsonFilePath)):
                                job_results['parts'].append({"partName": "Setting DashboardData file ownership: " + filename, "result": "Pass"})
                            else:
                                errorTitle = 'Datafile Parsing error'
                                errorBody = "Error Setting DashboardData file ownership: " + filename
                                errPrint(errorTitle + ': ', errorBody)
                                worker.OVDM.sendMsg(errorTitle,errorBody)
                                job_results['parts'].append({"partName": "Setting DashboardData file ownership: " + filename, "result": "Fail"})
                        else:
                            errorTitle = 'Datafile Parsing error'
                            errorBody = "Error Writing DashboardData file: " + filename
                            errPrint(errorTitle + ': ', errorBody)
                            worker.OVDM.sendMsg(errorTitle,errorBody)
                            job_results['parts'].append({"partName": "Writing Dashboard file: " + filename, "result": "Fail"})

                        newManifestEntries.append({"type":dd_type, "dd_json": jsonFilePath.replace(baseDir + '/',''), "raw_data": rawFilePath.replace(baseDir + '/','')})
            else:
                errPrint("No JSON output recieved from file", filename)
                removeManifestEntries.append({"dd_json": jsonFilePath.replace(baseDir + '/',''), "raw_data": rawFilePath.replace(baseDir + '/','')})

                #job_results['parts'].append({"partName": "Parsing JSON output from file " + filename, "result": "Fail"})
                if err:
                    errPrint(err)
        else:
            debugPrint("File is of unknown datatype")
            removeManifestEntries.append({"dd_json": jsonFilePath.replace(baseDir + '/',''), "raw_data":rawFilePath.replace(baseDir + '/','')})

            if err:
                errPrint(err)

        worker.send_job_status(job, int(10 + 70*float(index)/float(fileCount)), 100)
        index += 1

    worker.send_job_status(job, 8, 10)

    if len(newManifestEntries) > 0:
        debugPrint("Updating Manifest file:", dataDashboardManifestFilePath)

        row_removed = 0

        try:
            #debugPrint("Open Dashboard Manifest file:", dataDashboardManifestFilePath)
            DashboardManifestFile = open(dataDashboardManifestFilePath, 'r')

            existingManifestEntries = json.load(DashboardManifestFile)

        except IOError:
            errPrint("Error Reading Dashboard Manifest file")
            job_results['parts'].append({"partName": "Reading pre-existing Dashboard manifest file", "result": "Fail"})
            return json.dumps(job_results)

        finally:
            #debugPrint("Closing Dashboard Manifest file")
            DashboardManifestFile.close()
            job_results['parts'].append({"partName": "Reading pre-existing Dashboard manifest file", "result": "Pass"})

        debugPrint("Entries to remove:", json.dumps(removeManifestEntries, indent=2))
        for removeEntry in removeManifestEntries:
            for idx, existingEntry in enumerate(existingManifestEntries):
                if removeEntry['raw_data'] == existingEntry['raw_data']:
                    del existingManifestEntries[idx]
                    row_removed += 1

                    if os.path.isfile(os.path.join(baseDir,removeEntry['dd_json'])):
                        os.remove(os.path.join(baseDir,removeEntry['dd_json']))
                        debugPrint("Orphaned dd_json file deleted")
                    break

        debugPrint("Entries to add/update:", json.dumps(newManifestEntries, indent=2))
        for newEntry in newManifestEntries:
            updated = False
            for existingEntry in existingManifestEntries:
                if newEntry['raw_data'] == existingEntry['raw_data']:
                    updated = True
                    job_results['files']['updated'].append(newEntry['dd_json'].replace(worker.cruiseID + '/',''))
                    break

            if not updated: #added
                job_results['files']['new'].append(newEntry['dd_json'].replace(worker.cruiseID + '/',''))
                existingManifestEntries.append(newEntry)

        if len(job_results['files']['new']):
            debugPrint(len(job_results['files']['new']), "row(s) added")
        if len(job_results['files']['updated']):
            debugPrint(len(job_results['files']['updated']), "row(s) updated")
        if row_removed:
            debugPrint(row_removed, "row(s) removed")

        if output_JSONDataToFile(worker, dataDashboardManifestFilePath, existingManifestEntries):
            job_results['parts'].append({"partName": "Writing Dashboard manifest file", "result": "Pass"})
        else:
            errPrint("Error Writing Dashboard manifest file")
            job_results['parts'].append({"partName": "Writing Dashboard manifest file", "result": "Fail"})
            return json.dumps(job_results)

    worker.send_job_status(job, 9, 10)

    if(setOwnerGroupPermissions(worker, dataDashboardManifestFilePath)):
        job_results['parts'].append({"partName": "Setting manifest file ownership", "result": "Pass"})
    else:
        errPrint("Error Setting manifest file ownership")
        job_results['parts'].append({"partName": "Setting manifest file ownership", "result": "Fail"})

    worker.send_job_status(job, 10, 10)

    return json.dumps(job_results)


def task_rebuildDataDashboard(worker, job):

    job_results = {
        'parts':[],
        'files':{
            'new':[],
            'updated':[]
        }
    }

    payloadObj = json.loads(job.data)
    debugPrint('Payload:', json.dumps(payloadObj, indent=2))

    baseDir = worker.shipboardDataWarehouseConfig['shipboardDataWarehouseBaseDir']
    cruiseDir = os.path.join(baseDir, worker.cruiseID)
    dataDashboardDir = os.path.join(cruiseDir, worker.OVDM.getRequiredExtraDirectoryByName('Dashboard Data')['destDir'])
    dataDashboardManifestFilePath = os.path.join(dataDashboardDir, dataDashboardManifestFN)

    collectionSystemTransfers = worker.OVDM.getCollectionSystemTransfers()
    
    worker.send_job_status(job, 1, 100)

    newManifestEntries = []

    collectionSystemTransferCount = len(collectionSystemTransfers)
    collectionSystemTransferIndex = 0
    for collectionSystemTransfer in collectionSystemTransfers:

        debugPrint('Processing data from:', collectionSystemTransfer['name'])

        processingScriptFilename = os.path.join(worker.OVDM.getDashboardDataProcessingScriptDir(), collectionSystemTransfer['name'].replace(' ','-') + worker.OVDM.getDashboardDataProcessingScriptSuffix())
        debugPrint("Processing Script Filename: " + processingScriptFilename)

        if not os.path.isfile(processingScriptFilename):
            debugPrint("Processing script for collection system not found, moving on.")
            worker.send_job_status(job, int(10 + (80*float(collectionSystemTransferIndex)/float(collectionSystemTransferCount))), 100)
            collectionSystemTransferIndex += 1
            continue

        collectionSystemTransferInputDir = os.path.join(cruiseDir, collectionSystemTransfer['destDir'])
        collectionSystemTransferOutputDir = os.path.join(dataDashboardDir, collectionSystemTransfer['destDir'])
        
        #build filelist
        fileList = build_filelist(collectionSystemTransferInputDir)
        fileCount = len(fileList)
        fileIndex = 0
        debugPrint(fileCount, 'file(s) to process')

        for filename in fileList:

            if worker.stop:
                break

            jsonFileName = filename.split('.')[0] + '.json'
            rawFilePath = os.path.join(collectionSystemTransferInputDir, filename)
            jsonFilePath = os.path.join(collectionSystemTransferOutputDir, jsonFileName)

            debugPrint("Processing file: " + rawFilePath)

            if os.stat(rawFilePath).st_size == 0:
                debugPrint("File is empty")
                continue

            s=' '
            command = ['python', processingScriptFilename, '--dataType', rawFilePath]

            debugPrint(s.join(command))

            proc = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            out, err = proc.communicate()

            if out:
                dd_type = out.rstrip('\n')
                debugPrint("Found to be type: " + dd_type)

                command = ['python', processingScriptFilename, rawFilePath]

                debugPrint(s.join(command))

                proc = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                out, err = proc.communicate()

                if out:
                    try:
                        outObj = json.loads(out)
                    except:
                        errorTitle = 'Datafile Parsing error'
                        errorBody = s.join(command)
                        errPrint(errorTitle + ': ', errorBody)
                        worker.OVDM.sendMsg(errorTitle,errorBody)
                        continue
                    else:
                        if 'error' in outObj:
                            errorTitle = 'Datafile Parsing error'
                            errorBody = outObj['error']
                            errPrint(errorTitle + ': ', errorBody)
                            worker.OVDM.sendMsg(errorTitle,errorBody)
                        elif output_JSONDataToFile(worker, jsonFilePath, outObj):
                            newManifestEntries.append({"type":dd_type, "dd_json": jsonFilePath.replace(baseDir + '/',''), "raw_data":rawFilePath.replace(baseDir + '/','')})
                else:
                    errPrint("No JSON output recieved from file " + filename)
                    #job_results['parts'].append({"partName": "Parsing JSON output from file " + filename, "result": "Fail"})
                    if err:
                        errPrint(err)
            else:
                debugPrint("File is of unknown datatype")
                if err:
                    debugPrint(err)

            worker.send_job_status(job, int(10 + (80*(float(collectionSystemTransferIndex) + (float(fileIndex)/float(fileCount)))/float(collectionSystemTransferCount))), 100)
#            debugPrint(fileIndex, '/', fileCount, float(fileIndex)/float(fileCount))
#            debugPrint(collectionSystemTransferIndex, '/', collectionSystemTransferCount, float(collectionSystemTransferIndex)/float(collectionSystemTransferCount))

#            debugPrint(int(10 + (80*(float(collectionSystemTransferIndex) + (float(fileIndex)/float(fileCount)))/float(collectionSystemTransferCount))))
            fileIndex += 1

            if worker.stop:
                debugPrint("Stopping")
                break

        job_results['parts'].append({"partName": "Processing " + collectionSystemTransfer['name'], "result": "Pass"})

        collectionSystemTransferIndex += 1

    worker.send_job_status(job, 90, 100)

    debugPrint("Update Dashboard Manifest file")
    if output_JSONDataToFile(worker, dataDashboardManifestFilePath, newManifestEntries):
        job_results['parts'].append({"partName": "Updating manifest file", "result": "Pass"})
    else:
        errPrint("Error updating manifest file")
        job_results['parts'].append({"partName": "Updating manifest file", "result": "Fail"})
        return json.dumps(job_results)

    worker.send_job_status(job, 95, 100)

    if(setOwnerGroupPermissions(worker, dataDashboardDir)):
        job_results['parts'].append({"partName": "Setting file/directory ownership", "result": "Pass"})
    else:
        errPrint("Error Setting file/directory ownership")
        job_results['parts'].append({"partName": "Setting file/directory ownership", "result": "Fail"})
        return json.dumps(job_results)

    worker.send_job_status(job, 99, 100)

    job_results['files']['updated'] = build_dashboardData_filelist(worker)

    worker.send_job_status(job, 10, 10)

    return json.dumps(job_results)


# -------------------------------------------------------------------------------------
# Main function of the script should it be run as a stand-alone utility.
# -------------------------------------------------------------------------------------
def main(argv):

    parser = argparse.ArgumentParser(description='Handle data dashboard related tasks')
    parser.add_argument('-d', '--debug', action='store_true', help=' display debug messages')

    args = parser.parse_args()
    if args.debug:
        global DEBUG
        DEBUG = True
        debugPrint("Running in debug mode")

    debugPrint('Creating Worker...')
    global new_worker
    new_worker = OVDMGearmanWorker()

    debugPrint('Defining Signal Handlers...')
    def sigquit_handler(_signo, _stack_frame):
        errPrint("QUIT Signal Received")
        new_worker.stopTask()

    def sigint_handler(_signo, _stack_frame):
        errPrint("INT Signal Received")
        new_worker.quitWorker()

    signal.signal(signal.SIGQUIT, sigquit_handler)
    signal.signal(signal.SIGINT, sigint_handler)

    new_worker.set_client_id('dataDashboard.py')

    debugPrint('Registering worker tasks...')
    debugPrint('   Task:', 'updateDataDashboard')
    new_worker.register_task("updateDataDashboard", task_updateDataDashboard)
    debugPrint('   Task:', 'rebuildDataDashboard')
    new_worker.register_task("rebuildDataDashboard", task_rebuildDataDashboard)

    debugPrint('Waiting for jobs...')
    new_worker.work()

# -------------------------------------------------------------------------------------
# Required python code for running the script as a stand-alone utility
# -------------------------------------------------------------------------------------
if __name__ == "__main__":
    main(sys.argv[1:])
