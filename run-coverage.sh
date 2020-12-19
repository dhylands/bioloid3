#!/bin/bash

set -x
coverage run --source=bioloid -m pytest
coverage report -m
