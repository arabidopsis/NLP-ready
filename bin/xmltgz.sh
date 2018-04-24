#!/bin/bash
D=$1
d=`date +"%Y-%m-%d"`
# use tar --keep-newer-files -xvzf xml-$d.tgz
tar cvzf xml-$D-$d.tgz $D/xml_* $D/failed_*
