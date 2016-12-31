#!/usr/local/bin/python3

from argparse import ArgumentParser as ArgParser

import os
import sys
import inspect

import pyparser
import pynotebook 


debuglevel = 0
opts = None

def debug(level, line):
    '''
    Write debug message to output
    '''

    call = inspect.stack()[1][3]

    if level <= debuglevel:
        print("DBG: %-10s %1d/%1d %s" % (call, level, debuglevel, line))


def version():
    '''
    print current version string
    '''
    print("%s: Version 1.0.0" % __file__)
    sys.exit(0)


def parse_arguments():
    '''
    Parse command line arguments
    '''
    parser = ArgParser()

    parser.add_argument("files", nargs="*")
    # parser.add_argument('--file',  action='store')

    parser.add_argument('--output', action='store', nargs="?", default="")
    parser.add_argument('--debug',  action='store', type=int, default=0)
    parser.add_argument('--dir',    action='store', type=str, default=".")
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--details', action='store_true')
    parser.add_argument('--verbose', dest="verbose",
                        action='store_true', default=True)
    parser.add_argument('--quiet', dest="verbose", action='store_false')
    parser.add_argument('--check', action='store_true')

    opts = parser.parse_args()

    # Print the version and exit
    if opts.version:
        version()

    if opts.check:
        opts.verbose = False

    # if opts.file:
    #    opts.files.append(opts.file)

    global debuglevel
    debuglevel = opts.debug

    return opts


def convert(parser, filename):
    global opts

    code = ""
    result = 0
    try:
        debug(4, "read file: %s" % filename)
        with open(filename) as f:
            code = [line.rstrip() for line in f.readlines()]

        debug(4, "parse: %s" % filename)
        parser.parse(filename)
    except Exception as err:
        if opts.check:
            result = 1
            print("Unexpected error:", err)
        else:
            raise err

    if opts.check:
        if result == 0:
            print("PARSE: %s" % filename)
        else:
            print("ERROR: parsing %s" % filename)

        sys.exit()

    if opts.details:
        print("Code:" + '-' * 75)
        for lineno, line in enumerate(code):
            print("%4d: %s" % (lineno, line))

        print("Result:" + '-' * 73)
        print(''.join(parser.result))

        print("Lines:" + '-' * 74)
        for key in parser.lines:
            print(key, parser.lines[key])

    notebook = pynotebook.Notebook(debuglevel=debuglevel)

    isLastLine = False

    output = opts.output
    if opts.output == None:
        output = filename[:-3] + '.ipynb'
        f_out=open(output, 'w')
    elif opts.output != "":
        f_out=open(output, 'w')
    else:
        f_out=sys.stdout
        
    debug(1, "convert %s to %s" % (filename, output))

    for line in parser.notebook():
        if line is None:
            debug(2, "last line:")
        
            f_out.write(notebook.cell("1", celltype, line))
        else:
            (_lineno, _line, change, celltype) = line

            if change:
                prefix=celltype
            else:
                prefix="-"

            debug(4, "%4s: change: %s prefix: %s %-60s" % (_lineno, change, prefix, _line))

            f_out.write(notebook.cell(change, celltype, _line))


def main():
    '''
    main programm
    '''
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

    #
    debug(4, "create parser")
    parser = pyparser.Parser(debuglevel=debuglevel)

    for fname in opts.files:
        convert(parser, fname)


if __name__ == '__main__':
    main()
