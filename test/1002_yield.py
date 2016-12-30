#!/usr/local/bin/python3

def gen1():
    mylist = range(3)
    for i in mylist:
        yield i*i

def gen2():
    yield

_gen = gen1()
for i in _gen:
    print(i)
