#!bash

python vcd_merge.py tests/master1.vcd tests/slave1-1.vcd tests/out.vcd

cmp tests/merged1.vcd tests/out.vcd
if [ $? -ne 0 ]; then
    echo FAIL
    exit
fi
rm tests/out.vcd