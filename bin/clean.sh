#!/bin/bash
for d in `ls data`
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
