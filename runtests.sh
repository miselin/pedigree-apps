#!/bin/sh

if [ "x$COVERAGE" = "x" ]; then COVERAGE=coverage; fi

$COVERAGE run --branch --source=. -m unittest discover -p '*_test.py'
$COVERAGE html -d coverage_html

pip install flake8

flake8 --exclude=./packages/builds,./newpacks,./i686 .
