#!/bin/bash
arg=''
issns=`python3.5 mlcode/cell.py issn`
d=$1
for issn in $issns
do
	if [ -d "$d/failed_$issn" ] ; then
		arg="$arg $d/failed_$issn"
	fi
	if [ -d "$d/xml_$issn" ] ; then
		arg="$arg $d/xml_$issn"
	fi
done
echo $arg
tar czf $d-cell.tgz $arg
