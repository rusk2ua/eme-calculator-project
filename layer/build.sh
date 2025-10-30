#!/bin/bash
# Build script for Lambda layer

mkdir -p python
pip install -r requirements.txt -t python/
cp ../src/eme_calculator.py python/
