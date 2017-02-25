#!/usr/bin/env python3

# Copyright (C) 2010-2011 Marcin Kościelnicki <koriakin@0x04.net>
# Copyright (C) 2010 Luca Barbieri <luca@luca-barbieri.com>
# Copyright (C) 2010 Marcin Slusarz <marcin.slusarz@gmail.com>
# All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice (including the next
# paragraph) shall be included in all copies or substantial portions of the
# Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

import sys
import rnn

startcol = 64

fouts = {}

def printdef(name, val, file):
    fout = fouts[file]
    fout.write("#define {}{} {}\n".format(name, " " * (startcol - len(name)), val))


def printvalue(val, shift):
    if val.varinfo.dead:
        return
    if val.value is not None:
        printdef(val.fullname, hex(val.value << shift), val.file)

def printtypeinfo(ti, prefix, shift, file):
    if isinstance(ti, rnn.TypeHex) or isinstance(ti, rnn.TypeInt):
        if ti.shr:
            printdef (prefix + "__SHR", str(ti.shr), file)
        if ti.min is not None:
            printdef (prefix + "__MIN", hex(ti.min), file)
        if ti.max is not None:
            printdef (prefix + "__MAX", hex(ti.max), file)
        if ti.align is not None:
            printdef (prefix + "__ALIGN", hex(ti.align), file)
    if isinstance(ti, rnn.TypeFixed):
        if ti.min is not None:
            printdef (prefix + "__MIN", hex(ti.min), file)
        if ti.max is not None:
            printdef (prefix + "__MAX", hex(ti.max), file)
        if ti.radix is not None:
            printdef (prefix + "__RADIX", str(ti.radix), file)
    if isinstance(ti, rnn.Enum) and ti.inline:
        for val in ti.vals:
            printvalue(val, shift)
    if isinstance(ti, rnn.Bitset) and ti.inline:
        for bitfield in ti.bitfields:
            printbitfield(bitfield, shift)

def printbitfield(bf, shift):
    if bf.varinfo.dead:
        return
    if isinstance(bf.typeinfo, rnn.TypeBoolean):
        printdef(bf.fullname, hex(bf.mask << shift), bf.file)
    else:
        printdef(bf.fullname + "__MASK", hex(bf.mask << shift), bf.file)
        printdef(bf.fullname + "__SHIFT", str(bf.low + shift), bf.file)
    printtypeinfo(bf.typeinfo, bf.fullname, bf.low + shift, bf.file)

def printdelem(elem, offset, strides):
    if elem.varinfo.dead:
        return
    if elem.length != 1:
        strides = strides + [elem.stride]
    offset = offset + elem.offset
    if elem.name:
        if strides:
            name = elem.fullname + '(' + ", ".join("i{}".format(i) for i in range(len(strides))) + ')'
            val = '(' + hex(offset) + "".join(" + {:x} * i{}".format(stride, i) for i, stride in enumerate(strides)) + ')'
            printdef(name, val, elem.file)
        else:
            printdef(elem.fullname, hex(offset), elem.file)
        if elem.stride:
            printdef(elem.fullname +"__ESIZE", hex(elem.stride), elem.file)
        if elem.length != 1:
            printdef(elem.fullname + "__LEN", hex(elem.length), elem.file)
        if isinstance(elem, rnn.Reg):
            printtypeinfo(elem.typeinfo, elem.fullname, 0, elem.file)
    fouts[elem.file].write("\n")
    if isinstance(elem, rnn.Stripe):
        for subelem in elem.elems:
            printdelem(subelem, offset, strides)

def print_file_info(fout, file):
    #struct stat sb;
    #struct tm tm;
    #stat(file, &sb);
    #gmtime_r(&sb.st_mtime, &tm);
    #char timestr[64];
    #strftime(timestr, sizeof(timestr), "%Y-%m-%d %H:%M:%S", tm);
    #fprintf(dst, "(%7Lu bytes, from %s)\n", (unsigned long long)sb->st_size, timestr);
    fout.write("\n")

def printhead(file, db):
    fout = fouts[file]
    fout.write("#ifndef {}\n".format(guard(file)))
    fout.write("#define {}\n".format(guard(file)))
    fout.write("\n")
    fout.write(
        "/* Autogenerated file, DO NOT EDIT manually!\n"
        "\n"
        "This file was generated by the rules-ng-ng headergen tool in this git repository:\n"
        "https://github.com/envytools/envytools/\n"
        "git clone https://github.com/envytools/envytools.git\n"
        "\n"
        "The rules-ng-ng source files this header was generated from are:\n")
    #struct stat sb;
    #struct tm tm;
    #stat(f.name, &sb);
    #gmtime_r(&sb.st_mtime, &tm);
    maxlen = max(len(file) for file in db.files)
    for file in db.files:
        fout.write("- {} ".format(file + " " * (maxlen - len(file))))
        print_file_info(fout, file)
    fout.write(
        "\n"
        "Copyright (C) ")
    #if(db->copyright.firstyear && db->copyright.firstyear < (1900 + tm.tm_year))
    #    fout.write("%u-", db->copyright.firstyear);
    #fout.write("%u", 1900 + tm.tm_year);
    if db.copyright.authors:
        fout.write(" by the following authors:")
        for author in db.copyright.authors:
            fout.write("\n- ")
            if author.name:
                fout.write(author.name)
            if author.email:
                fout.write(" <{}>".format(author.email))
            if author.nicknames:
                fout.write(" ({})".format(", ".join(author.nicknames)))
    fout.write("\n")
    if db.copyright.license:
        fout.write("\n{}\n".format(db.copyright.license))
    fout.write("*/\n\n\n")


def guard(file):
    return ''.join(c.upper() if c.isalnum() else '_' for c in file)


def process(mainfile):
    db = rnn.Database()
    rnn.parsefile(db, mainfile)
    db.prep()

    for file in db.files:
        fouts[file] = open(file.replace('/', '_') + '.h', 'w')
        printhead(file, db)

    for enum in db.enums:
        if not enum.inline:
            for val in enum.vals:
                printvalue(val, 0)

    for bitset in db.bitsets:
        if not bitset.inline:
            for bitfield in bitset.bitfields:
                printbitfield(bitfield, 0)

    for domain in db.domains:
        if domain.size:
            printdef(domain.fullname + "__SIZE", hex(domain.size), domain.file)
        for elem in domain.elems:
            printdelem(elem, 0, [])

    for file in fouts:
        fouts[file].write("\n#endif /* {} */\n".format(guard(file)))
        fouts[file].close()

    return db.estatus

if len(sys.argv) < 2:
    sys.stdout.write ("Usage:\n"
            "\theadergen file.xml\n"
        )
    sys.exit(2)

sys.exit(process(sys.argv[1]))
