#!/bin/bash
d=`date +"%Y-%m-%d"`
zip -r cleaned-$d.zip data/cleaned/*
