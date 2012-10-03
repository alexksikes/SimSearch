#! /usr/bin/env python
import sys
import getopt
import simsearch


def query(index_path, matching_keywords=False):
    index = simsearch.ComputedIndex(index_path)
    query_handler = simsearch.QueryHandler(index)

    while(True):
        sample_ids = ' '.join(map(str, query_handler.get_sample_item_ids()))
        print '>> Enter some item ids: (try %s)' % sample_ids

        item_ids = map(int, raw_input().split())
        result_set = query_handler.query(item_ids, max_results=10000)

        print result_set

        if matching_keywords:
            ids = [id for id, sc in result_set.log_scores][0:10]
            show_matching_keywords(ids, query_handler)


def show_matching_keywords(ids, query_handler):
    item_scores = query_handler.get_detailed_scores(ids)

    print 'Top matching keywords (%.2f sec.):' % \
        query_handler.get_detailed_scores.time_taken

    for scores, id in zip(item_scores, ids):
        print '*' * 80
        print 'id = %s' % id
        print ' '.join('%s - %.2f' % (t, s) for t, s in scores['scores'])
        print '*' * 80


def usage():
    print 'Usage: python query_index.py index_path'
    print
    print 'Description:'
    print '    Load and then query a similarity search index.'
    print
    print 'Options:'
    print '    -v, --verbose     : also show matching keywords'
    print '    -h, --help        : this help message'


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'vh', ['verbose', 'help'])
    except getopt.GetoptError:
        usage(); sys.exit(2)

    verbose = False
    for o, a in opts:
        if o in ('-v', '--verbose'):
            verbose = True
        elif o in ('-h', '--help'):
            usage(); sys.exit()

    if len(args) < 1:
        usage()
    else:
        query(args[0], verbose)

if __name__ == '__main__':
    main()
