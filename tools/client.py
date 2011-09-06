# Author: Alex Ksikes

import urllib

from simsearch import bsets

class SimilaritySearchClient:
    def __init__(self, server_port=8000):
        self.base_url = 'http://localhost:%s/?' % server_port

    def query(self, item_ids):
        url = self.base_url + '&'.join('similar=%s' % id for id in item_ids)
        txt = urllib.urlopen(url).read()
        return bsets.ResultSet.loads(txt)
    
def usage():
    print 'Usage: python client.py [options]'
    print
    print 'Description:' 
    print '    Query a similarity index served on the default port 8000.'
    print 
    print '-p, --port <number>  ->    query an index served in a different port'
    print '-h, --help           ->    this help message'

import sys, getopt
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'p:h', ['port=', 'help'])
    except getopt.GetoptError:
        usage(); sys.exit(2)
    
    port = 8000
    for o, a in opts:
        if o in ('-p', '--port'):
            port = int(a)
        elif o in ('-h', '--help'):
            usage(); sys.exit()
    
    cl = SimilaritySearchClient(port)
    
    while(True):
        print 'Enter some item ids:'
        item_ids = map(int, raw_input().split())
        print cl.query(item_ids)
    
if __name__ == "__main__":
    main()