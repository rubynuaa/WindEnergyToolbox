'''
Created on 17/07/2014

@author: MMPE
'''
import unittest
from wetb.hawc2.cmp_test_cases import CompareTestCases
import numpy as np

class Test(CompareTestCases):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.ref_path = r'test_files/cmp_test_cases/ref/'
        self.test_path = r'test_files/cmp_test_cases/test1/'

    def test_compare_sel(self):
        self.compare_sel(self.ref_path + 'test1.sel', self.test_path + 'test1.sel')

    def test_compare_sel_different_number_of_lines(self):
        self.assertRaisesRegex(AssertionError, "16 != 15 : \nNumber of lines differs in", self.compare_sel, self.ref_path + 'test2.sel', self.test_path + 'test2.sel')

    def test_compare_sel_different_header(self):
        self.compare_sel(self.ref_path + 'test3.sel', self.test_path + 'test3.sel')

    def test_compare_sel_difference(self):
        self.assertRaisesRegex(AssertionError, "     2      bea1 angle                     deg        shaft_rot angle",
                               self.compare_sel, self.ref_path + 'test4.sel', self.test_path + 'test4.sel')

    def test_compare_contents_dat(self):
        self.compare_dat_contents(self.ref_path + 'test1.dat', self.test_path + 'test1.dat')

    def test_compare_dat_contents_difference(self):
        self.assertRaisesRegex(AssertionError, "  2.00000E-02", self.compare_dat_contents, self.ref_path + 'test3.dat', self.test_path + 'test3.dat')

    #def test_compare_plot_difference(self):
    #    self.assertRaisesRegex(AssertionError, "Difference in the the values of:\n1 Time", self.compare_dat_plot, self.ref_path + 'test3', self.test_path + 'test3')

#    def test_compare_folder(self):
#        self.compare_folder(r'test_files/ref/', r'test_files/test/', 'ref', 'test1')


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
