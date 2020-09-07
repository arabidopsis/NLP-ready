#!/bin/bash
if [ "$#" -ne 2 ] ; then
        echo "expecting CSV (paper_urls.csv) grep string as arguments" >&2
        exit 1
fi
cat $1 | grep $2 | cut -d, -f2,3 | uniq | awk -F, -e '{print "\""$1"\": " "\""$2"\"," }'

