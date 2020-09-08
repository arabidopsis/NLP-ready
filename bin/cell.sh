#!/bin/bash
if [ "$#" -ne 1 ] ; then
        echo "expecting data directory as argument" >&2
        exit 1
fi
DIRNAME="$(dirname $0)"
code="$DIRNAME/../"
arg=''
issns=`(cd $code; python -m nlpready.cell issn)`
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
