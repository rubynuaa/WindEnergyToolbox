'''
Created on 18/11/2015

@author: MMPE
'''
import unittest
from wetb.hawc2.log_file import LogFile, is_file_open, \
    INITIALIZATION, SIMULATING, DONE, PENDING
import time
from wetb.hawc2 import log_file
import threading
import os
from wetb.hawc2.htc_file import HTCFile

def simulate(file, wait):
    with open(file, 'r') as fin:
        lines = fin.readlines()
    file = file + "_"
    with open(file, 'w'):
        pass
    time.sleep(.1)
    for l in lines:
        with open(file, 'a+') as fout:
            fout.write(l)
        if "Turbulence generation starts" in l or "Log file output" in l:
            time.sleep(0.2)
        time.sleep(wait)

class Test(unittest.TestCase):


    def test_from_htcfile(self):
        htcfile = HTCFile('test_files/logfiles/model/htc/dlc14_iec61400-1ed3/dlc14_wsp10_wdir000_s0000.htc')
        logfile = LogFile.from_htcfile(htcfile, 'test_files/logfiles/model/')
        self.assertEqual(logfile.status, DONE)

    def test_missing_logfile(self):
        f = 'test_files/logfiles/missing.log'
        logfile = LogFile(f, 200)
        logfile.update_status()
        self.assertEqual(logfile.pct, 0)
        self.assertEqual(logfile.status, log_file.MISSING)


    def test_is_file_open(self):
        f = 'test_files/logfiles/test.log'
        with open(f, 'a+'):
            self.assertTrue(is_file_open(f))
        with open(f, 'r'):
            self.assertTrue(is_file_open(f))
        self.assertFalse(is_file_open(f))

    def test_simulation_init_error(self):
        f = 'test_files/logfiles/init_error.log'
        logfile = LogFile(f, 2)
        logfile.update_status()
        self.assertEqual(logfile.pct, 100)
        self.assertEqual(logfile.status, DONE)
        self.assertEqual(logfile.errors, ['*** ERROR *** No line termination in command line            8'])

    def test_init(self):
        f = 'test_files/logfiles/init.log'
        logfile = LogFile(f, 200)
        logfile.update_status()
        self.assertEqual(logfile.pct, 0)
        self.assertEqual(logfile.status, INITIALIZATION)
        self.assertEqual(logfile.errors, [])

    def test_turbulence_generation(self):
        f = 'test_files/logfiles/turbulence_generation.log'
        logfile = LogFile(f, 200)
        logfile.update_status()
        self.assertEqual(logfile.pct, 0)
        self.assertEqual(logfile.status, INITIALIZATION)
        self.assertEqual(logfile.errors, [])
        self.assertEqual(logfile.lastline, "Turbulence generation starts ...")

    def test_simulation(self):
        f = 'test_files/logfiles/simulating.log'
        logfile = LogFile(f, 2)
        logfile.update_status()
        self.assertEqual(logfile.pct, 25)
        self.assertEqual(logfile.status, SIMULATING)
        self.assertEqual(logfile.errors, [])



    def test_finish(self):
        f = 'test_files/logfiles/finish.log'
        logfile = LogFile(f, 200)
        self.assertEqual(logfile.pct, 100)
        self.assertEqual(logfile.status, DONE)
        self.assertEqual(logfile.errors, [])
        self.assertEqual(logfile.elapsed_time, 0.8062344)

    def test_HAWC2Version(self):
        f = 'test_files/logfiles/finish.log'
        logfile = LogFile(f, 200)
        self.assertEqual(logfile.hawc2version, "HAWC2MB 11.8")


    def test_simulation_error(self):
        f = 'test_files/logfiles/simulation_error.log'
        logfile = LogFile(f, 2)
        self.assertEqual(logfile.pct, 100)
        self.assertEqual(logfile.status, DONE)
        self.assertEqual(logfile.errors, ['*** ERROR *** Error opening out .dat file'])

    def test_simulation_error2(self):
        f = 'test_files/logfiles/simulation_error2.log'
        logfile = LogFile(f, 2)
        self.assertEqual(logfile.pct, 100)
        self.assertEqual(logfile.status, DONE)
        self.assertEqual(logfile.errors[0], '*** ERROR *** Out of limits in user defined shear field - limit value used')
        self.assertEqual(logfile.error_str(), '30 x *** ERROR *** Out of limits in user defined shear field - limit value used')



    def check(self, logfilename, phases, end_status, end_errors=[]):
        return
        logfile = LogFile(logfilename + "_", 2)
        logfile.clear()
        if os.path.isfile(logfile.filename):
            os.remove(logfile.filename)
        t = threading.Thread(target=simulate, args=(logfilename, 0.0001))
        t.start()
        last_status = None
        last_pct = 0
        while logfile.pct >= 0 and logfile.status != DONE:
            logfile.update_status()
            if logfile.status != last_status or logfile.pct != last_pct:
                last_status = logfile.status
                last_pct = logfile.pct
                if logfile.status in phases:
                    phases.remove(logfile.status)
            time.sleep(0.01)
        self.assertEqual(logfile.pct, 100)
        self.assertEqual(logfile.status, end_status)
        self.assertEqual(logfile.errors, end_errors)
        self.assertFalse(phases)
        t.join()
        os.remove(logfile.filename)


    def test_realtime_test(self):
        self.check('test_files/logfiles/finish.log',
                   phases=[PENDING, INITIALIZATION, SIMULATING, DONE],
                   end_status=DONE)

    def test_realtime_test2(self):
        self.check('test_files/logfiles/init_error.log',
           phases=[PENDING, INITIALIZATION, SIMULATING, DONE],
           end_status=DONE,
           end_errors=['*** ERROR *** No line termination in command line            8'])

    def test_realtime_test_simulation_error(self):
        self.check('test_files/logfiles/simulation_error.log',
                   [PENDING, INITIALIZATION, SIMULATING, DONE],
                   DONE, ['*** ERROR *** Error opening out .dat file'])

    def test_realtime_test_turbulence(self):
        self.check('test_files/logfiles/finish_turbulencegeneration.log',
                   phases=[PENDING, INITIALIZATION, SIMULATING, DONE],
                   end_status=DONE,
                   end_errors=[])


    def test_remaining(self):
        logfilename = 'test_files/logfiles/finish.log'
        logfile = LogFile(logfilename + "_", 2)
        logfile.clear()
        if os.path.isfile(logfile.filename):
            os.remove(logfile.filename)
        t = threading.Thread(target=simulate, args=(logfilename, 0.01))
        t.start()
        last_status = None
        last_pct = 0
        estimated_simulation_time = None
        while logfile.pct >= 0 and logfile.status != DONE:
            if estimated_simulation_time is None and logfile.remaining_time is not None:
                endtime = time.time() + logfile.remaining_time
            #print (logfile.pct, logfile.remaining_time, logfile.lastline)
            logfile.update_status()
            if logfile.status != last_status or logfile.pct != last_pct:
                last_status = logfile.status
                last_pct = logfile.pct
            time.sleep(0.1)
        t.join()
        self.assertLess(abs(time.time() - endtime), 0.1)
        os.remove(logfile.filename)


    def test_remaining_str(self):
        logfile = LogFile("f", 2)
        logfile.remaining_time = 5
        self.assertEqual(logfile.remaining_time_str(), "00:05")
        logfile.remaining_time = 60 + 5
        self.assertEqual(logfile.remaining_time_str(), "01:05")
        logfile.remaining_time = 3600 + 120 + 5
        self.assertEqual(logfile.remaining_time_str(), "1:02:05")




if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_logfile']
    unittest.main()