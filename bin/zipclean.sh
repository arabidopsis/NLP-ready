#!/bin/bash
c=$1
d=`date +"%Y-%m-%d"`
zip -r cleaned-$c-$d.zip $c/cleaned/*
