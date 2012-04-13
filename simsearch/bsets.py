"""This is module is an implementation of Bayesian Sets."""

__all__ = ['Indexer', 'ComputedIndex', 'QueryHandler', 'load_index']

from scipy import sparse
from MySQLdb import cursors
import numpy
import MySQLdb
import random
import cPickle as pickle

import utils
logging = utils.basic_logger

class Indexer(object):
    """"This class is used to index the list of features fetch from a database. 
    
    It will create a computed index which can then be queried.
    """
    def __init__(self, config):
        """Builds an indexer given a configuration file.
        
        The configuration file must have the db parameters and a list of sql queries
        to fetch the features from.
        """
        # get params from config dict ...
        self.db_params = config.db_params
        self.sql_features = config.sql_features 
        
    def index_dataset(self, limit):
        """Indexes the data into a computed index.
        
        For now only bag of words are implemented. 
        Override _make_datasets to index other feature types.
        """
        # connect to database
        self._init_database()
        
        # make the dataset
        logging.info('Building the dataset from sql table ...')
        self._make_dataset(limit)
        logging.info('%.2f sec.', self._make_dataset.time_taken)
        
        # compute hyperparameters
        logging.info('Computing hyper parameters ...')
        self._compute_hyper_parameters()
        logging.info('%.2f sec.', self._compute_hyper_parameters.time_taken)
    
    def _init_database(self):
        self.db_params['use_unicode'] = True
        self.db_params['cursorclass'] = cursors.SSCursor
        self.db = MySQLdb.connect(**self.db_params)
    
    @utils.time_func
    def _make_dataset(self, limit=''):
        # initialize dataset variables
        X = {}
        self.item_id_to_index = {}
        self.index_to_item_id = {}
        self.feat_to_index = {}
        self.index_to_feat = {}
        
        # go through the features in our sql table
        limit = limit and 'limit %s' % limit or ''
        for sql in self.sql_features:
            cur = self.db.cursor()
            sql = '%s %s' % (sql, limit)
            logging.info('SQL: %s', sql)
            cur.execute(sql)
            
            for i, (id_val, feat_val) in enumerate(cur):
                if id_val not in self.item_id_to_index:
                    r = len(self.item_id_to_index)
                    self.item_id_to_index[id_val] = r
                    self.index_to_item_id[r] = id_val
                    X[r] = [] 
                    
                if feat_val not in self.feat_to_index:
                    c = len(self.feat_to_index)
                    self.feat_to_index[feat_val] = c
                    self.index_to_feat[c] = feat_val
                
                r = self.item_id_to_index[id_val]
                c = self.feat_to_index[feat_val]
                X[r].append(c)
            
            cur.close()
        
        # cleaning up
        cur.close()
        self.db.close()
        
        # give some simple statistics
        logging.info('Done processing the dataset.')
        self.no_items = len(self.item_id_to_index)
        self.no_features = len(self.feat_to_index)
        logging.info('Number of items: %s', self.no_items)
        logging.info('Number of features: %s', self.no_features)
        
        # make a sparse matrix from the dataset
        logging.info('Constructing sparse matrix from dataset ...')
        self.X = sparse.lil_matrix((self.no_items, self.no_features))
        for r in X.keys():
            for c in X[r]:
                self.X[r,c] = 1
            
        # and convert it to csr for matrix operations
        logging.info('Converting sparse matrix to csr ...')
        self.X = self.X.tocsr()
        
    @utils.time_func
    def _compute_hyper_parameters(self, c=2):
        self.mean = self.X.mean(0)
        
        self.alpha = c * self.mean
        self.beta = c * (1 - self.mean)
        
        self.alpha_plus_beta = self.alpha + self.beta
        self.log_alpha_plus_beta = numpy.log(self.alpha_plus_beta) 
        
        self.log_alpha = numpy.log(self.alpha)
        self.log_beta = numpy.log(self.beta)
        
    def get_computed_index(self):
        """Returns a computed index.
        
        This must be called after index_dataset.
        """
        return ComputedIndex(
            no_items         = self.no_items,
            X                = self.X,
            item_id_to_index = self.item_id_to_index,
            index_to_item_id = self.index_to_item_id,
            alpha            = self.alpha,
            beta             = self.beta,
            alpha_plus_beta  = self.alpha_plus_beta,
            log_alpha        = self.log_alpha,
            log_beta         = self.log_beta,
            db_params        = self.db_params,
            index_to_feat    = self.index_to_feat)
    
    def save_index(self, path):
        """Saves the computed index into a pickled file.
        
        This must be called after index_dataset.
        """
        self.get_computed_index().dump(path)
        
class ComputedIndex(utils.Serializable):
    """"This class represents a computed index which is returned by indexer.
    
    A computed index contains the matrix in CSR format and all hyper paramters 
    already computed.
    
    A computed index can then be queried using a QueryHandler object or saved 
    into a file.
    """
    def __init__(self, no_items, X, item_id_to_index, index_to_item_id,
        alpha, beta, alpha_plus_beta, log_alpha, log_beta, db_params, index_to_feat):
        utils.auto_assign(self, locals())
    
    def dump(self, index_path):
        """Saves this index into a file.
        """
        logging.info('Saving the index to %s ...', index_path)
        dump = super(ComputedIndex, self).dump
        dump(index_path)
        logging.info('%.2f sec.', dump.time_taken)
        
    @staticmethod
    def load(index_path):
        """Load this picked index into an object.
        """
        logging.info('Loading index from %s in memory ...', index_path)
        load = utils.Serializable.load
        index = load(index_path)
        logging.info('%.2f sec.', load.time_taken)
        
        return index
        
    def get_sample_item_ids(self):
        """Returns some sample item ids from this index.
        """
        return [self.index_to_item_id[i] for i in random.sample(xrange(self.no_items), 10)]
    
class QueryHandler(object):
    """This class is used to query a computed index.
    """
    def __init__(self, computed_index, caching=False):
        utils.auto_assign(self, vars(computed_index))
        self.time_taken = 0
            
    def query(self, item_ids, max_results=100):
        """Query the given computed against the item ids.
        """
        # check the query is valid
        if not self.is_valid_query(item_ids):
            return self.empty_results
        
        # make query vector
        logging.info('Computing the query vector ...')
        self._make_query_vector()
        logging.info('%.2f sec.', self._make_query_vector.time_taken)
        
        # compute log scores
        logging.info('Computing log scores ...')
        self._compute_scores()
        logging.info('%.2f sec.', self._compute_scores.time_taken)

        # sort the results by log scores
        logging.info('Get the top %s log scores ...', max_results)
        self._order_indexes_by_scores(max_results)
        logging.info('%.2f sec.', self._order_indexes_by_scores.time_taken)
        
        return self.results
    
    def get_detailed_scores(self, query_item_ids, result_ids, max_terms=20):
        # if the query vector was not computed, we need to recompute it!
        if not hasattr(self, 'q'):
            if not self.is_valid_query(query_item_ids):
                return None
            else:
                logging.info('Computing the query vector ...')
                self._make_query_vector()
                logging.info('%.2f sec.', self._make_query_vector.time_taken)
                self.time_taken += self._make_query_vector.time_taken 
                
        # computing deatailed scores for the chosen items
        logging.info('Computing detailed scores ...')
        scores = self._compute_detailed_scores(result_ids, max_terms)
        logging.info('%.2f sec.', self._compute_detailed_scores.time_taken)
        
        self.time_taken += self._compute_detailed_scores.time_taken
        return utils._O(scores=scores, time=self.time_taken)

    @utils.time_func
    def is_valid_query(self, item_ids):
        self.item_ids = item_ids
        self._item_ids = [id for id in item_ids if id in self.item_id_to_index]
        return self._item_ids != []
    
    @utils.time_func
    def _make_query_vector(self):
        item_ids = self._item_ids
        N = len(item_ids)
        
        sum_xi = self.X[self.item_id_to_index[item_ids[0]]]
        for id in item_ids[1:]:
            sum_xi = sum_xi + self.X[self.item_id_to_index[id]]
        
        alpha_bar = self.alpha + sum_xi
        beta_bar = self.beta + N - sum_xi
        log_alpha_bar = numpy.log(alpha_bar)
        log_beta_bar = numpy.log(beta_bar)
        
        self.c = (self.alpha_plus_beta - numpy.log(self.alpha_plus_beta + N) + log_beta_bar - self.log_beta).sum()
        self.q = log_alpha_bar - self.log_alpha - log_beta_bar + self.log_beta
        
    @utils.time_func
    def _compute_scores(self):
        self.scores = self.X * self.q.transpose()
        self.scores = numpy.asarray(self.scores).flatten()
        self.log_scores = self.c + self.scores
        
    @utils.time_func
    def _order_indexes_by_scores(self, max_results=100):
        if max_results == -1:
            self.ordered_indexes = xrange(len(self.log_scores))
        else:
            self.ordered_indexes = utils.argsort_best(self.log_scores, max_results, reverse=True)
            logging.info('Got %s indexes ...', len(self.ordered_indexes))

    @utils.time_func  
    def _compute_detailed_scores(self, item_ids, max_terms=20):
        """Returns detailed statistics about the matched items.
        """
        scores = []
        for id in item_ids:
            if id not in self.item_id_to_index:
                scores.append(dict(total_score=0, scores=[]))
                continue
            
            xi = self.X[self.item_id_to_index[id]]
            xi_ind = xi.indices
            
            feat = (self.index_to_feat[i] for i in xi_ind)
            
            qi = self.q.transpose()[xi_ind]
            qi = numpy.asarray(qi).flatten()
            
            sc = sorted(zip(feat, qi), key=lambda x: (x[1], x[0]), reverse=True)
            total_score = qi.sum()
            
            scores.append(dict(total_score=total_score, scores=sc[0:max_terms]))
        return scores
    
    def _update_time_taken(self, reset=False):
        self.time_taken = (
            + getattr(self._make_query_vector, 'time_taken', 0)
            + getattr(self._compute_scores, 'time_taken', 0)
            + getattr(self._order_indexes_by_scores, 'time_taken', 0)
            + getattr(self._compute_detailed_scores, 'time_taken', 0)
        )
        
    @property
    def results(self):
        """Returns the results as a ResultSet object.
        
        This must be called after the index has been queried.
        """
        self._update_time_taken()
        
        def get_tuple_item_id_score(scores):
            return [(self.index_to_item_id[i], scores[i]) for i in self.ordered_indexes]
            #return ((self.index_to_item_id[i], scores[i]) for i in self.ordered_indexes)
        
        return ResultSet(
            time = self.time_taken,
            total_found = len(self.ordered_indexes),
            query_item_ids  = self.item_ids,
            _query_item_ids = self._item_ids,
            log_scores = get_tuple_item_id_score(self.log_scores)
        )
    
    @property
    def empty_results(self):
        return ResultSet.get_empty_result_set(query_item_ids=self.item_ids, _query_item_ids=self._item_ids)
            
class ResultSet(utils.Serializable):
    """This class represents the results returned by a query handler.
    
    It holds the log scores amongst other variables.
    """
    def __init__(self, time, total_found, query_item_ids, _query_item_ids, log_scores):
        utils.auto_assign(self, locals())
    
    def __str__(self):
        s = 'You look for (after cleaning up) :\n%s \n' % '\n'.join(map(str, self._query_item_ids))
        s += 'Found %s in %.2f sec. \n' % (self.total_found, self.time)
        s += 'Best results found:\n'
        for id, log_score in self.log_scores[0:10]:
            s+= 'id = %s, log score = %s\n' % (id, log_score)
        return s
    
    @staticmethod
    def get_empty_result_set(**kwargs):
        o = dict(
            time            = 0,
            total_found     = 0,
            query_item_ids  = [],
            _query_item_ids = [],
            log_scores      = []
        )
        o.update(kwargs)
        return ResultSet(**o)
    
class Searcher(object):
    """Creates a query handler from a pickled computed index.
    """ 
    def __call__(self, computed_index_path):
        index = ComputedIndex.load(computed_index_path)
        return QueryHandler(index)

def load_index(index_path, once=None):
    """Loads a pickled computed index into a ComputedIndex object.
    """
    if once and len(once):
        return once
    return ComputedIndex.load(index_path)

def load_index_to(index_path, to):
    """Loads a pickled computed index into a ComputedIndex object.
    """
    if n and len(once):
        return once
    return ComputedIndex.load(index_path)

def handle_query(item_ids, computed_index, max_results=100):
    """Queries a computed index against the item ids.
    """
    return QueryHandler(computed_index).query(item_ids, max_results)