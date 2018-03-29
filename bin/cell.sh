#!/bin/bash
arg=''
issns=`python3.5 mlcode/cell.py issn`
for issn in $issns
do
    arg="$arg data/failed_$issn data/xml_$issn"
done
echo $arg
tar czf cell.tgz $arg
