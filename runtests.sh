#!/bin/sh

set -e

if [ "x$COVERAGE" = "x" ]; then COVERAGE=coverage; fi

$COVERAGE run --branch --source=. -m unittest discover -p '*_test.py'
$COVERAGE html -d coverage_html

if [ "x$VIRTUAL_ENV" != "x" ]; then pip install flake8; fi

flake8 --exclude=./packages/builds,./newpacks,./i686,./venv,./downloads,./package-template,./packages,./pup/build,./standalone-*,'*_test.py' .
