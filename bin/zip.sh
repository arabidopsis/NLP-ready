#!/bin/bash
d=`date +"%Y-%m-%d"`
zip -r rakesh-$d.zip data/cleaned_*/ data/xml_*/
