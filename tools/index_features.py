#! /usr/bin/env python

from simsearch import bsets, utils

def make_index(config_path, index_name, **options):
    cf = utils.parse_config_file(config_path, **options)
    
    indexer = bsets.Indexer(cf)
    indexer.index_dataset(cf.get('limit'))
    indexer.save_index(index_name)
    
def usage():
    print 'Usage: python index_features.py [options] config_path'
    print
    print 'Description:' 
    print '    Creates a similarity search index called "index.dat" given a config file.'
    print 
    print 'Options:' 
    print '    -o, --out         : different index name than "./index.dat"'
    print '    -l, --limit       : loop only over the first "limit" number of items'
    print '    -h, --help        : this help message'

import sys, getopt
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'o:l:h', ['out=', 'limit=', 'help'])
    except getopt.GetoptError:
        usage(); sys.exit(2)
    
    index_name, options = 'index.dat', {} 
    for o, a in opts:
        if o in ('-o', '--out'):
            index_name = a
        elif o in ('-l', '--limit'):
            options['limit'] = int(a)
        elif o in ('-h', '--help'):
            usage(); sys.exit()
    
    if len(args) < 1:
        usage()
    else:
        make_index(args[0], index_name, **options)
        
if __name__ == '__main__':
    main()
