#!/bin/bash
sphinx-apidoc -f -o source ../dino
make html
make text
