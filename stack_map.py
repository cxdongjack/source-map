#!/usr/bin/python
import collections, json, sys, bisect, re

SmapState = collections.namedtuple('SmapState', ['dst_line', 'dst_col', 'src', 'src_line', 'src_col', 'name'])
B64 = dict((c, i) for i, c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'))

def parse_vlq(segment):
    values = []

    cur, shift = 0, 0
    for c in segment:
        val = B64[c]
        val, cont = val & 0b11111, val >> 5
        cur += val << shift
        shift += 5

        if not cont:
            cur, sign = cur >> 1, cur & 1
            if sign:
                cur = -cur
            values.append(cur)
            cur, shift = 0, 0

    if cur or shift:
        raise Exception('leftover cur/shift in vlq decode')

    return values

def parse_smap(f):
    smap = json.load(f)
    sources = smap['sources']
    names = smap['names']
    mappings = smap['mappings']
    lines = mappings.split(';')

    dst_col, src_id, src_line, src_col, name_id = 0, 0, 0, 0, 0
    for dst_line, line in enumerate(lines):
        segments = line.split(',')
        dst_col = 0
        for segment in segments:
            if not segment:
                continue
            parse = parse_vlq(segment)
            dst_col += parse[0]

            src = None
            name = None
            if len(parse) > 1:
                src_id += parse[1]
                src = sources[src_id]
                src_line += parse[2]
                src_col += parse[3]

                if len(parse) > 4:
                    name_id += parse[4]
                    name = names[name_id]

            yield SmapState(dst_line + 1, dst_col + 1, src, src_line + 1, src_col + 1, name)

if len(sys.argv) == 1:
    print 'Usage: %s js_map_file < js_stack_file' % sys.argv[0]
    sys.exit()

maps = list(parse_smap(open(sys.argv[1])))
regex = re.compile(r':(\d+):(\d+)')

for line in sys.stdin:
    line = line.rstrip('\n')
    print line

    result = regex.search(line)

    if result:
        origin = maps[bisect.bisect([(x[0], x[1]) for x in maps], (int(result.group(1)), int(result.group(2)))) - 1]
        print '\t%s:%d:%d:%s' % (origin.src, origin.src_line, origin.src_col, origin.name)
