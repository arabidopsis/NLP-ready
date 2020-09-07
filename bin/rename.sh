#!/bin/bash
if [ "$#" -ne 1 ] ; then
        echo "expecting data directory as argument" >&2
        exit 1
fi
for d in $1/xml_* $1/failed_*
do
    if [ $d = "$1/xml_epmc" ]  || [ $d = "$1/xml_elsevier" ] ; then
        continue
    fi
    if [ $d = "$1/failed_epmc" ]  || [ $d = "$1/failed_elsevier" ] ; then
        continue
    fi
    echo "renaming $d"
    for f in $d/*.xml
    do
        g=`basename $f`
        g="${g%.*}"
        mv $f $d/$g.html
    done
done
