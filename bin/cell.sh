#!/bin/bash
arg=''
for issn in '1097-4172' '0092-8674' '1090-2104'
do
    arg="$arg data/failed_$issn data/xml_$issn"
done
echo $arg
tar cvzf cell.tgz $arg
