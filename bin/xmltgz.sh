#!/bin/bash
d=`date +"%Y-%m-%d"`
# use tar --keep-newer-files -xvzf xml-$d.tgz
tar cvzf xml-$d.tgz xml_* failed_*