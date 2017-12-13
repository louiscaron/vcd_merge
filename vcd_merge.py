#!python

from itertools import dropwhile, takewhile, izip
from collections import defaultdict
import argparse
import textwrap

class VCD(object):
    def __init__(self, file):
        self._file = file
        self.name = file.name
        self.tokenizer = (word for line in file for word in line.split() if word)
        self.idcodes = dict()

    def __cmp__(self, other):
        if self.now < other.now:
            return -1
        elif self.now == other.now:
            return 0
        else:
            return 1
            
    def close(self):
        self._file.close()
        self._file = None
    
    def closed(self):
        return self._file == None

    def add_var(self, id_code, var_type, size, final_id_code, reference):
        self.idcodes[id_code] = (var_type, size, final_id_code, reference)
        
    def timescale_fs(self):
        "Return the timescale value as a multiple of fs"
        time_unit = {'fs':1, 'ps':10**3, 'ns':10**6, 'us':10**9, 'ms':10**12, 's':10**15}
        time_number = {'1': 1, '10': 10, '100': 100}
        n, u = self.timescale.split()
        return time_number[n] * time_unit[u]

    def final_id_codes(self):
        "Return the list of the final identifier codes"
        return [i[2] for i in self.idcodes.values()]

    def uses_id_code(self, id_code):
        "Return True if the identifier_code belongs to the VCD else False"
        return id_code in self.final_id_codes()
    
    def final_id_code(self, id_code):
        return self.idcodes[id_code][2]



def copy_tokens(file, keyword, tokens):
    file.write(keyword)
    if len(tokens):
        file.write(' ' + ' '.join(tokens))
    file.write(" $end\n")

def parse_error(vcds, vcd, keyword):
    raise "Don't understand keyword: " + keyword

def drop_declaration(vcds, vcd, keyword):
    return tuple(takewhile(lambda x: x != "$end", vcd.tokenizer))
    
def save_declaration(vcds, vcd, keyword):
    tokens = tuple(takewhile(lambda x: x != "$end", vcd.tokenizer))
    vcd.__setattr__(keyword.lstrip('$'), " ".join(tokens) )
    return tokens

vcd_date = save_declaration
vcd_timescale = save_declaration
vcd_version = save_declaration

def vcd_var(vcds, vcd, keyword):
    tokens = tuple(takewhile(lambda x: x != "$end", vcd.tokenizer))
    var_type, size, local_id_code, reference = tokens
    
    new_code = chr(33)
    def next_code(code):
        lcode = list(code)
        for i, c in enumerate(lcode):
            if c < chr(126):
                lcode[i] = chr(ord(lcode[i]) + 1)
                break
            else:
                lcode[i] = chr(33)
                if i == len(code) - 1:
                    lcode.append(chr(33))
                    break
        return ''.join(lcode)
    
    final_id_code = local_id_code

    # change the identifier code if it is already in use
    while filter(lambda x: x.uses_id_code(final_id_code), vcds):
        final_id_code = new_code
        new_code = next_code(new_code)
    
    if local_id_code != final_id_code:
        print("{}: replacing var id '{}' with '{}'".format(vcd.name, local_id_code, final_id_code)) 

    vcd.add_var(local_id_code, var_type, size, final_id_code, reference)
    
    # return the tuple of tokens using the final code
    return (var_type, size, final_id_code, reference)


keyword2handler = {
    # declaration_keyword ::=
    "$comment": drop_declaration,
    "$date": vcd_date,
    "$scope": drop_declaration,
    "$timescale": vcd_timescale,
    "$upscope": drop_declaration,
    "$var": vcd_var,
    "$version": vcd_version,
}
keyword2handler = defaultdict(parse_error, keyword2handler)

def vcd_merge(vcdfiles, outfile):
    vcds = []
    for vcdfile in vcdfiles:
        vcd = VCD(vcdfile)
        vcds.append(vcd)
        for token in vcd.tokenizer:
            if token == "$enddefinitions":
                drop_declaration(vcds, vcd, token)
                break
            subtokens = keyword2handler[token](vcds, vcd, token)
            if (vcdfile == vcdfiles[0]) or token in ["$scope", "$upscope", "$var"]:
                copy_tokens(outfile, token, subtokens)
    # generate the end definitions line
    outfile.write("\n$enddefinitions $end\n")
    
    # check the timescales (must all be lower or equal to that of the master)
    vcd_master = vcds[0]
    vcd_master.timescale_mult = 1
    fs_master = vcd_master.timescale_fs()
    for vcd in vcds[1:]:
        fs_slave = vcd.timescale_fs()
        assert fs_slave >= fs_master, 'timescale {} in {} is smaller than {} in {}'.format(
            vcd.timescale, vcd.name, vcd_master.timescale, vcd_master.name)
        vcd.timescale_mult = fs_slave/fs_master

    # chomp till first simulation time
    for vcd in vcds:
        for token in vcd.tokenizer:
            c, rest = token[0], token[1:]
            if c == '$':
                # skip $dump* tokens and $end tokens in sim section
                continue
            elif c == '#':
                vcd.now = int(rest, 10) * vcd.timescale_mult
                break
            else:
                raise AssertionError("Unexpected token before simu time in {}: {}".format(vcd.name, token))
        
    def handle(vcd):
        for token in vcd.tokenizer:
            c, rest = token[0], token[1:]
            if c == '$':
                # skip $dump* tokens and $end tokens in sim section
                continue
            elif c == '#':
                vcd.now = int(rest, 10) * vcd.timescale_mult
                return
            elif c in '01xXzZ':
                # the local identifier code is stored in rest
                outfile.write(c + vcd.final_id_code(rest) + '\n')
            elif c in 'bBrRsS':
                outfile.write(token + ' ' + vcd.final_id_code(vcd.tokenizer.next()) + '\n')
            else:
                raise AssertionError("Unexpected token in {}: {}".format(vcd.name, token))
        vcd.close()
    
    while vcds:
        # retrieve the earliest time in all VCDs
        curtime = min(vcds).now
        outfile.write('#' + str(curtime)+'\n')
        # generate the value change for all VCDs that have activity at that time
        map(handle, filter(lambda v: v.now == curtime, vcds))
        # remove VCDs that are finished
        vcds = filter(lambda v: not v.closed(), vcds)
    

# use a customer formatter to do raw text and add default values
class CustomerFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter):
    pass

argparser = argparse.ArgumentParser(formatter_class=CustomerFormatter,
                                    description=textwrap.dedent('''
    Merge VCD files
    '''))

argparser.add_argument('infiles', action='store', type=argparse.FileType('r'), nargs='+',
    help='VCD files to merge')
argparser.add_argument('outfile', action='store', type=argparse.FileType('w'),
    help='merged VCD file to write to')

my_args = argparser.parse_args()

vcd_merge(my_args.infiles, my_args.outfile)
