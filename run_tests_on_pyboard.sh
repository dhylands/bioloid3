#!/bin/bash

rm -rf bioloid/__pycache__ tests/__pycache__
rshell 'rsync upy /flash; rsync bioloid /flash/bioloid; rsync tests /flash/tests; cp run_tests.py /flash; repl ~ import run_tests'
