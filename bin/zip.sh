#!/bin/bash
if [ "$#" -ne 1 ] ; then
        echo "expecting data directory as argument" >&2
        exit 1
fi
c=$1
d=`date +"%Y-%m-%d"`
zip -r xml-$c-$d.zip $c/xml_*/
