#! /usr/bin/env python
import sys
import getopt
import simsearch

from simsearch import utils


def make_index(config_path, **opts):
    opts = utils.parse_config_file(config_path, **opts)
    index = simsearch.FileIndex(opts.index_path, mode=opts.mode)
    iter_feat = simsearch.BagOfWordsIter(opts.db_params, opts.sql_features, opts.get('limit', 0))
    simsearch.Indexer(index, iter_feat).index_data()


def usage():
    print 'Usage: python index_features.py [options] config_path'
    print
    print 'Description:'
    print '    Creates a similarity search index given a configuration file.'
    print '    This uses bag of words features and will create an index called'
    print '    ./sim-index/ unless otherwise speciied.'
    print
    print 'Options:'
    print '    -o, --out         : path to the index (default ./sim-index/)'
    print '    -m, --mode        : "write" or "append" to the index (defaut write)'
    print '    -l, --limit       : loop only over the first "limit" number of items'
    print '    -h, --help        : this help message'


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
            'o:m:v:l:h', 
            ['out=', 'mode=', 'verbose=', 'limit=', 'help'])
    except getopt.GetoptError:
        usage(); sys.exit(2)

    _opts = dict(index_path='sim-index', mode='write')
    for o, a in opts:
        if o in ('-o', '--out'):
            _opts['index_path'] = a
        if o in ('-m', '--mode'):
            if a in ('append', 'write'):
                _opts['mode'] = a
        elif o in ('-l', '--limit'):
            _opts['limit'] = int(a)
        elif o in ('-h', '--help'):
            usage(); sys.exit()

    if len(args) < 1:
        usage()
    else:
        make_index(args[0], **_opts)

if __name__ == '__main__':
    main()
