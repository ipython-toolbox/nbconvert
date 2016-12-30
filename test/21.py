import os
import sys
import re

'''
This is the docstring
over two lines
'''

#
# This should be a comment
#
class SampleClass1():
    def __init__(self):
        return

class SampleClass2():

    def __init__(self):
        '''
        TEST
        '''
        return

    def func1(self, par1, par2):
        return

    def func2():
        pass

def func1():
    '''
    Docstring Line1
    '''
    pass


def func2():
    '''
    Docstring Line1
    Docstring Line2
    '''
    pass


sys.exit(0)
