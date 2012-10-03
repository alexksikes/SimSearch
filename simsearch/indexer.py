"""This is module used to create similarity search indexes.

An index is made of 4 files called .xco, .yco, .ids and .fts. 
The files .xco and .yco holds the x and y coordinates of the matrix. This 
matrix represents whether a particular item id has a particular feature.

The file .ids is used to keep track of the matrix indices with respect to 
the item ids. The line number as the index in the matrix for the given the 
item id in the matrix. In a similar way, the file .fts is used to keep track 
of the features.
"""

__all__ = ['Indexer', 'BagOfWordsIter', 'FileIndex']

import os
import scipy
from scipy import sparse
import codecs
import MySQLdb
from MySQLdb import cursors

import utils
from utils import logger


class Indexer(object):
    def __init__(self, index, iter_features):
        """ An indexer takes a FileIndex object and an iterator.
        
        The iterator must return the couple (item id, feature). The item id
        must be an integer, whereas the feature must be a unique string 
        representing the feature (utf8 encoded or a unicode).
        """
        if not isinstance(index, FileIndex):
            self.index = FileIndex(index, 'write')
        self.index = index
        self.iter_features = iter_features
        
    @utils.show_time_taken
    def index_data(self):
        with self.index:
            for id, feat in self.iter_features:
                self.index.add(id, feat)
        self.show_stats()
                
    def show_stats(self):
        logger.info('Done processing the dataset.')
        logger.info('Number of items: %s', len(self.index.ids))
        logger.info('Number of features: %s', len(self.index.fts))
        

class BagOfWordsIter(object):
    """ This class implements the bag of words model and is passed to Indexer
    object.
    """
    def __init__(self, db_params, sql_features, limit=0):
        """ Takes the parameters of the database (only MySQL is supported for now) 
        and a list of SQL statements to fetch the data.
        
        The SQL statements must select 2 fields, respectively the item id
        and the keyword.
        """
        self.db_params = dict(use_unicode=True, cursorclass=cursors.SSCursor)
        self.db_params.update(db_params)
        
        self.db = MySQLdb.connect(**self.db_params)
        self.sql_features = sql_features        
        if limit:
            self.sql_features = ['%s limit %s' % (sql, limit) 
                for sql in sql_features]
    
    def __iter__(self):
        for sql in self.sql_features:
            c = self.db.cursor()
            logger.info('SQL: %s', sql)
            c.execute(sql)
            for id, feat in c:
                if isinstance(feat, int) or isinstance(feat, long):
                    feat = utils._unicode(feat)
                yield id, feat
            c.close()
        self.db.close()


class FileIndex(object):
    """ This class is used to manipulate the index. 
    
    The index can be opened in 3 different modes. The mode 'write' is used 
    to create the index. It will overwrite any other existing index. 
    The mode 'read' is used to load the index in memory. Finally the mode 
    'append' appends data to an already existing index.
    """
    def __init__(self, index_path, mode='read', feat_enc='utf8'):
        self.index_path = index_path
        self.mode = mode
        self.ids = {}
        self.fts = {}
        
        self.xco = []
        self.yco = []
        self.X = None
                
        if mode not in ('read', 'append', 'write'):
            raise Exception('Incorrect mode %s, choose read, write \
                or append' % self.mode)
        
        if mode == 'read':
            self._read()
        elif mode == 'append':
            self._read()
            self._open_index_files('append')
        else:
            if not os.path.exists(index_path):
                os.makedirs(index_path)
            self._open_index_files('write')
            
    def _read(self):
        self._open_index_files(mode='read')
        for ext in ('ids', 'fts', 'xco', 'yco'):
            self._read_index_file(ext)
        if self.mode == 'append':
            self._make_coo()
        self._close_index_files()
    
    @utils.show_time_taken
    def _make_coo(self):
        logger.info('Making coordinate matrix for append ...')
        data = scipy.ones(len(self.xco))
        self.X = sparse.csr_matrix((data, (self.xco, self.yco)))
        
    def add(self, id, feat):
        """ Adds the given (id, feature) to the index.
        
        The id must an int and the feature must be a unique string representation
        of the feature. The feature is expected to be unicode or utf8 encoded.
        
        This method does not check whether (id, feature) has already been inserted
        to the index.
        """
        if not self._check_input(id, feat):
            return
        feat = utils._unicode(feat)
        if id not in self.ids:
            x = len(self.ids)
            self.ids[id] = x
            self.fids.write('%s\n' % id)
        if feat not in self.fts:
            y = len(self.fts)
            self.fts[feat] = y
            self.ffts.write('%s\n' % feat)
        (x, y) = (self.ids[id], self.fts[feat])
        if not self._in_coo(x, y):
            self.fxco.write('%s\n' % x)
            self.fyco.write('%s\n' % y)
    
    def close(self):
        self._close_index_files()
    
    def _in_coo(self, x, y):
        in_coo = False
        if self.mode == 'append':
            try:
                in_coo = bool(self.X[x, y])
            except IndexError:
                pass
        return in_coo
                
    def _check_input(self, id, feat):
        success = False
        if self.mode == 'read':
            raise Exception('Can\'t write to read only index!')
        elif id is None:
            logger.warn('Undefined item id skipping ... skipping.')
        elif not isinstance(id, (int, long)):
            raise Exception('List of ids must be integers!')
        elif not isinstance(feat, basestring):
            logger.warn('Feature "%s" is not string or a unicode ... converting.' % feat)
            success = True
        elif feat is None:
            logger.warn('Undefined feature for item %s ... skipping.' % id)
        else:
            success = True
        return success
    
    def _open_index_files(self, mode='read'):
        mode = dict(write='wb', append='ab', read='rb')[mode]
        self.fxco = self._new_index_file_handle('xco', mode)
        self.fyco = self._new_index_file_handle('yco', mode)
        self.fids = self._new_index_file_handle('ids', mode)
        self.ffts = self._new_index_file_handle('fts', mode)
    
    def _close_index_files(self):
        for f in ('fxco', 'fyco', 'fids', 'ffts'):
            if hasattr(self, f):
                getattr(self, f).close()
    
    def _new_index_file_handle(self, ext, mode='rb'):
        if ext == 'fts':
            return codecs.open(os.path.join(self.index_path, '.'+ext), mode, encoding='utf8')
        else:
            return open(os.path.join(self.index_path, '.'+ext), mode)
        
    @utils.show_time_taken
    def _read_index_file(self, ext):
        f = self.__dict__['f'+ext]
        logger.info('Reading file %s ...' % f.name)
        if ext == 'fts':
            vals = f.read().split('\n')[:-1]
        else:
            vals = scipy.fromfile(f, sep='\n', dtype=scipy.int32)
        if ext == 'fts' or ext == 'ids':
            vals = dict((v, i) for i, v in enumerate(vals))
        self.__dict__[ext] = vals
           
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        self._close_index_files()
