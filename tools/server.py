# Author: Alex Ksikes

import re
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

from simsearch import bsets, utils
logging = utils.basic_logger
        
class RequestHandler(BaseHTTPRequestHandler):
    p_url = re.compile('similar=(\d+)')
    
    def _writeheaders(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8") 
        self.end_headers()
    
    def do_GET(self):
        cls = RequestHandler
        item_ids = map(int, cls.p_url.findall(self.path))
        
        self._writeheaders()
        if item_ids:
            results = self.do_query(item_ids)
            self.wfile.write(results.dumps())
            
    def do_query(self, item_ids):
        sever_cls = SimilaritySearchServer
        return bsets.QueryHandler(sever_cls.computed_index).query(item_ids, sever_cls.config.max_items)

class SimilaritySearchServer(utils.ThreadingMixIn, HTTPServer):
    allow_reuse_address = 1
    
    def __init__(self, index_path, config=dict()):
        self.index_path = index_path
        self.server_port = config.get('server_port', 8000)
        SimilaritySearchServer.config = config
        
        server_address = ('', self.server_port)
        HTTPServer.__init__(self, server_address, RequestHandler)
    
    def load_index(self):
        cls = SimilaritySearchServer 
        cls.computed_index = bsets.ComputedIndex.load(self.index_path)
    
    def serve_forever(self):
        logging.info('Listening on port %s', self.server_port)
        HTTPServer.serve_forever(self)
        # or? ThreadingMixIn.serve_forever()
    
def run_server(index_path, config):
    server = SimilaritySearchServer(index_path, config)
    server.load_index()
    server.serve_forever()
    
def usage():
    print 'Usage: python server.py [options] index_path'
    print
    print 'Description:' 
    print '    Serve a given similarity search index.'
    print 
    print '-c, --config <path>  ->  use the given configuration file'
    print '-p, --port <number>  ->  serve on port (default of 8000)'
    print
    print '-h, --help           ->  this help message'
    

import sys, getopt
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'c:p:h', ['config=', 'port=', 'help'])
    except getopt.GetoptError:
        usage(); sys.exit(2)
    
    config_path = '' 
    options = dict(server_port=8000, max_items=10000)
    for o, a in opts:
        if o in ('-c', '--config'):
            config_path = a
        elif o in ('-p', '--port'):
            options['server_port'] = int(a)
        elif o in ('-h', '--help'):
            usage(); sys.exit()
    
    if config_path:
        cf = utils.parse_config_file(config_path, **options)
    else:
        cf = utils._O(options)    
    if len(args) < 1:
        usage()
    else:
        run_server(args[0], cf)

if __name__ == "__main__":
    main()