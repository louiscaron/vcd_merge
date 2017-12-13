# vcd_merge
A script to merge several VCD files into a single one

Based on [toggle count sample|http://paddy3118.blogspot.com/2008/03/writing-vcd-to-toggle-count-generator.html] code from Donald 'Paddy' McCarthy:

e.g.
python vcd_merge.py master.vcd slave1.vcd slave2.vcd slave3.vcd merged.vcd

The first input file in the list is the master VCD file: the declaration
part is copied entirely in the output file (version, date, comment, timescale).
The other files in the list are considered slaves: only the variable declaration
is copied in the output file.  Furthermore if their timescale is less than the
master timescale it will generate an error.  Finally, if their identifier codes
are already in use, they will be replaced (this will generate a message on the
screen).

