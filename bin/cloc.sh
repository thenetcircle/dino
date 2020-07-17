#!/bin/bash
cloc --fullpath --not-match-d "site|dino/admin/static|docs|dist|\.git|\.idea|__pycache__|dino\.egg-info" .
