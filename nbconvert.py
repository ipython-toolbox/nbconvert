#!/usr/local/bin/python3

import os
import sys
import inspect

import ast

import pyparser as pyparser

from argparse import ArgumentParser as ArgParser

debuglevel = 0

opts=None

def debug(level, line):
    '''
    Write debug message to output
    '''

    call = inspect.stack()[1][3]
    this = inspect.stack()[0][3]

    if level <= debuglevel:
        print("DBG: %-10s %1d/%1d %s" % (call, level, debuglevel, line))


def parse_arguments():
    parser = ArgParser()

    parser.add_argument("files", nargs="*")
    # parser.add_argument('--file',  action='store')
    
    parser.add_argument('--output', action='store')
    parser.add_argument('--debug',  action='store', type=int, default=0)

    parser.add_argument('--dir',    action='store', type=str, default=".")

    parser.add_argument('--version', action='store_true')

    parser.add_argument('--details', action='store_true')
    
    parser.add_argument('--verbose', dest="verbose", action='store_true', default=True)
    parser.add_argument('--quiet', dest="verbose", action='store_false')
    
    parser.add_argument('--check', action='store_true')

    opts = parser.parse_args()

    # Print the version and exit
    if opts.version:
        version()
        sys.exit(0)

    if opts.check:
        opts.verbose=False

    #if opts.file:
    #    opts.files.append(opts.file)

    #
    global debuglevel
    debuglevel = opts.debug

    return opts

def convert(parser, file):
    global opts

    code = ""
    result = 0
    try:
        debug(4, "read file: %s" % file)
        with open(file) as f:
            code = f.readlines()

        debug(4, "parse: %s" % file)
        parser.parse(code)
    except Exception as err:
        if opts.check:
            result = 1
            print("Unexpected error:", err)
        else:
            raise err
            
    if opts.check:   
        if result == 0:
            print("PARSE: %s" % file)
        else:
            print("ERROR: parsing %s" % file)
    else:
        if opts.details:
            print("Code:")
            for lineno, line in enumerate(code):
                print("%4d: %s" % (lineno, line))

            print("Result:")
            print(''.join(parser.result))

            print("Lines:")
            print(parser.lines)

        print("Source")
        parser.source()
        

def main():
    global opts
    opts = parse_arguments()

    files = []
    if opts.files == []:
        for dpath, _, filenames in os.walk(opts.dir):
            for fname in filenames:
                if fname[-3:] == '.py':
                    files.append(dpath + '/' + fname)
    else:
        files = opts.files

    debug(4, "files: %r" % files)

    debug(4, "create parser")
    parser = pyparser.Parser(debuglevel=debuglevel)

    for file in opts.files:
        convert(parser, file)


if __name__ == "__main__":
    main()
