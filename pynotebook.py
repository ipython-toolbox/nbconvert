#!/usr/local/bin/python3

import os
import sys
import inspect


class Notebook():

    debuglevel = 0
    isfirstcell = True

    indent = ' \t'

    def __init__(self, debuglevel=4):
        self.debuglevel = debuglevel

    def debug(self, level, line):
        '''
        Write debug message to output
        '''

        call = inspect.stack()[1][3]
        this = inspect.stack()[0][3]

        if level <= self.debuglevel:
            print("DBG: %-10s %s" % (call, line))

    def nb_start(self):
        return '{\t"cells":\n\t[\n'

    def nb_end(self):
        return ' \t],\n' \
            ' \t"metadata": {\n' \
            ' \t\t"anaconda-cloud": {},\n' \
            ' \t\t"kernelspec": { "display_name": "python3", "language": "python", "name": "python3" },\n' \
            ' \t\t"language_info": { "codemirror_mode": { \n' \
            ' \t\t\t"name": "ipython", "version": 3 },\n' \
            ' \t\t\t"file_extension": ".py",\n' \
            ' \t\t\t"mimetype": "text/x-python",\n' \
            ' \t\t\t"name": "python",\n' \
            ' \t\t\t"nbconvert_exporter": "python",\n' \
            ' \t\t\t"pygments_lexer": "ipython3",\n' \
            ' \t\t\t"version": "3.4.2"\n' \
            ' \t\t\t}\n' \
            ' \t\t},' \
            ' \t\t"nbformat": 4, "nbformat_minor": 0\n' \
            '}'

    def cell(self, change, celltype, line):
        '''
        write a code cell:
        type = 'code' or 'markdown'
        '''

        self.debug(2, "change: %s/%s first: %r line: '%s'" %
                   (change, celltype, 1 if self.isfirstcell else 0, line))

        info = "c: %s t: %s f: %r" % (change, celltype, self.isfirstcell)
        content = ""

        if self.isfirstcell:
            content = self.nb_start()
        else:
            if change:
                content += "\"\n" + self.indent * 3 + "]\n" + self.indent * 2 + "}"
            else:
                content += "\\n\"" 
            content += ",\n"

        if celltype == "C":
            typ = "code"
        elif celltype == "M":
            typ = "markdown"
            if line == "":
                line = " "

        if change:
            content += self.indent * 2 + \
                "{" + self.indent + "\"cell_type\": \"" + typ + "\", "

            if typ == "code":
                content += "\"execution_count\": 2, \"metadata\": { \"collapsed\": false }, \"outputs\": []"
            else:
                content += "\"metadata\": {}"

            content += ", \n" + self.indent * 3 + "\"source\": [\n"

        content += self.indent * 4 + "\"" + str(line)

        if line is None:
            content = "\"\n" 
            content += self.indent * 3 + "]\n" + self.indent * 2 + "}" + "\n"
            content += self.nb_end()

        #
        self.isfirstcell = False

        return content

    def convert(self):
        '''
        Main
        '''

        args = parse_arguments()

        files = []
        if args.input == None:
            for dpath, _, filenames in os.walk(args.dir):
                for fname in filenames:
                    if fname[-3:] == '.py':
                        files.append(dpath + '/' + fname)
        else:
            files = [args.input]

        parser = Parse(files[0])
        line = next(parser)

        fsm = FSM()

        while True:
            line = next(parser)
            debug(4, "line = '%s'" % line)
            if line == None:
                break

            (state, line) = fsm.input(line)

            print('%10s: %s' % (state, line))

        sys.exit(0)

        for py_path in files:
            nb_path = py_path[:-3] + '.ipynb'

            debug(4, "MAIN: convert %s to %s" % (py_path, nb_path))

            with open(py_path, 'r') as f_in, open(nb_path, 'w') as f_out:
                debug(4, "MAIN: write notebook start header")
                f_out.write(NB_START())

                remove_blank_lines = False
                ignore_line = False
                is_newcell = True
                is_firstcell = True

                lines = []

                state = ""

                for line in f_in.read().splitlines():
                    ignore_line = True

                    debug(4, "MAIN: isnew=%r removeblank=%r handle next line: '%s'" % (
                        is_newcell, remove_blank_lines, line))

                    linetyp = line[0:3]

                    if linetyp == '#!/':
                        state = "in hashbang"
                        remove_blank_lines = True

                        debug(4, "skip hashbang")
                        continue

                    if len(line) == 0 and remove_blank_lines:
                        debug(4, "skip empty line")
                        continue
                    else:
                        remove_blank_lines = False

                    #
                    if linetyp in ['def']:
                        celltyp = "code"
                        is_newcell = True
                    elif linetyp in ['###']:
                        celltyp = "markdown"
                        debug(4, "set is_newcell to %r" % is_newcell)
                        is_newcell = True
                    elif linetyp in ['"""', "'''"]:
                        ignore_line = True

                        celltyp = "markdown"

                        if state == "in docstring":
                            debug(4, "set is_newcell to %r" % is_newcell)
                            is_newcell = True
                            state = ""
                        else:
                            is_newcell = False
                            state = "in docstring"
                    else:
                        celltyp = "code"

                    if is_newcell:

                        if len(lines) == 0:
                            debug(4, "no lines skip create cell state=%s, typ=%s" % (
                                state, celltyp))
                        else:
                            debug(4, "create cell state=%s, typ=%s" %
                                  (state, celltyp))
                            content = cell(
                                lines, celltyp, isfirstcell=is_firstcell)
                            lines = []

                            debug(4, "write line %s" % line)
                            f_out.write(content)

                            is_newcell = False
                            is_firstcell = False

                    if not ignore_line:
                        line = line.replace(
                            '"', ' \\"').replace(' \t', '   ')

                    lines.append(line)

                debug(4, "MAIN: write last line")
                content = cell(lines, celltyp, isfirstcell=is_firstcell)
                f_out.write(content)

                debug(4, "MAIN: write notebook end header")
                f_out.write(NB_END())

            print("Created", nb_path)
