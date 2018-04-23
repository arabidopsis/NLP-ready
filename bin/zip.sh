#!/bin/bash
c=$1
d=`date +"%Y-%m-%d"`
zip -r xml-$c-$d.zip $c/xml_*/
