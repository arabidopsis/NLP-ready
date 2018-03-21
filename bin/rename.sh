#!/bin/bash
for d in data/xml_* data/failed_*
do
    if [ $d = 'data/xml_epmc' ]  || [ $d = 'data/xml_elsevier' ] ; then
        continue
    fi
    if [ $d = 'data/failed_epmc' ]  || [ $d = 'data/failed_elsevier' ] ; then
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