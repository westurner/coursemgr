#!/bin/sh
NEW=`git diff | egrep -e '^\+' | grep -v '+++' | wc -l`
DEL=`git diff | egrep -e '^\-' | grep -v '\-\-\-' | wc -l`
echo "$NEW new lines"
echo "$DEL deleted lines"
