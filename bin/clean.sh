#!/bin/bash
if [ "$#" -ne 1 ] ; then
        echo "expecting data directory as argument" >&2
        exit 1
fi
for d in `ls $1`
do
    if [ $d == 'xml_epmc' ] || [ $d == 'xml_elsevier' ]  || \
       [ $d == 'failed_epmc' ] || [ $d == 'failed_elsevier' ] ; then
        continue
    fi
    for f in `ls data/$d/*.xml 2>/dev/null`
    do
        echo $f
        rm $f
    done
done
