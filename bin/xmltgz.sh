#!/bin/bash
if [ "$#" -ne 1 ] ; then
        echo "expecting data directory as argument" >&2
        exit 1
fi
D=$1
d=`date +"%Y-%m-%d"`
# use tar --keep-newer-files -xvzf xml-$d.tgz
tar cvzf xml-$D-$d.tgz $D/xml_* $D/failed_*
