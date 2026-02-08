""" 
    Test file with bad code for code review agent , add more example to this
"""

import os
import sys
import json   # unused import


PASSWORD = "admin123"   # hardcoded secret


def calculate(a, b, debug=False, cache={}):   # mutable default argument
    if debug == True:     # bad boolean comparison
        print("Debug mode is on")

    try:
        result = a / b
    except:               # bare except
        return None

    return result


def run(cmd):
    # dangerous use of eval
    return eval(cmd)


def process(data):
    list = []     # shadows built-in name

    for i in range(len(data)):   # non-pythonic loop
        list.append(data[i])

    return list


def unused_function():
    x = 10   # unused variable
    y = 20
    return x


class usermanager:   # class name should be CamelCase

    def __init__(self, name):
        self.Name = name   # inconsistent attribute naming

    def PrintUser(self):   # method name should be snake_case
        print("User:", self.Name)


if __name__ == "__main__":
    print(calculate(10, 0))
    print(run("2 + 2"))
    um = usermanager("Prateek")
    um.PrintUser()

