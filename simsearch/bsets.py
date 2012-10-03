"""This is module is an implementation of Bayesian Sets."""

__all__ = ['ComputedIndex', 'QueryHandler', 'load_index']

import random
import scipy
from scipy import sparse

import indexer
import utils
from utils import logger


class ComputedIndex(utils.Serializable):
    """"This class represents a computed index.

    A computed index contains the matrix in CSR format and all hyper parameters
    already computed.

    A computed index can then be queried using a QueryHandler object or saved
    into a file.
    """
    def __init__(self, index_path):
        """ Creates a computed index from the path to an index.
        """
        index = self._load_file_index(index_path)
        self._create_indexes(index.ids, index.fts)
        self._compute_matrix_to_csr(index.xco, index.yco)
        self._compute_hyper_parameters()
        index.close()
            
    @utils.show_time_taken
    def _load_file_index(self, index_path):
        logger.info("Loading file index ...")
        return indexer.FileIndex(index_path, mode='read')
        
    @utils.show_time_taken
    def _create_indexes(self, ids, fts):
        logger.info("Creating indices ...")
        self.item_id_to_index = dict(ids)
        self.index_to_item_id = dict((i, id) for id, i in ids.iteritems())
        self.index_to_feat = dict((i, ft) for ft, i in fts.iteritems())
        self.no_items = len(ids)
        self.no_features = len(fts)

    @utils.show_time_taken
    def _compute_matrix_to_csr(self, xco, yco):
        logger.info("Creating CSR matrix ...")
        data = scipy.ones(len(xco))
        self.X = sparse.csr_matrix((data, (xco, yco)))
            
    @utils.show_time_taken
    def _compute_hyper_parameters(self, c=2):
        logger.info("Computing hyper parameters ...")
        self.mean = self.X.mean(0)
        self.alpha = c * self.mean
        self.beta = c * (1 - self.mean)
        self.alpha_plus_beta = self.alpha + self.beta
        self.log_alpha_plus_beta = scipy.log(self.alpha_plus_beta)
        self.log_alpha = scipy.log(self.alpha)
        self.log_beta = scipy.log(self.beta)
        
        
class QueryHandler(object):
    """This class is used to query a computed index.
    """
    def __init__(self, computed_index):
        utils.auto_assign(self, vars(computed_index))
        self.computed_index = computed_index
        self.time = 0

    def query(self, item_ids, max_results=100):
        """Queries the given computed against the given item ids.
        """
        item_ids = utils.listify(item_ids)
        if not self.is_valid_query(item_ids):
            return self.empty_results

        logger.info('Computing the query vector ...')
        self._make_query_vector()
        logger.info('Computing log scores ...')
        self._compute_scores()
        logger.info('Get the top %s log scores ...', max_results)
        self._order_indexes_by_scores(max_results)

        return self.results

    def get_detailed_scores(self, item_ids, query_item_ids=None, max_terms=20):
        """Returns detailed statistics about the matched items.

        This will assume the same items previously queried unless otherwise
        specified by 'query_item_ids'.
        """
        item_ids = utils.listify(item_ids)

        logger.info('Computing detailed scores ...')
        scores = self._compute_detailed_scores(item_ids, query_item_ids, max_terms)
        
        self._update_time_taken()
        return scores

    def get_sample_item_ids(self):
        """Returns some sample item ids from the index.
        """
        return [self.index_to_item_id[i] for i in random.sample(xrange(self.no_items), 10)]

    def is_valid_query(self, item_ids):
        """Checks whether the item ids are within the index.
        """
        self.item_ids = item_ids
        self._item_ids = [id for id in item_ids if id in self.item_id_to_index]
        return self._item_ids != []

    @utils.show_time_taken
    def _make_query_vector(self):
        item_ids = self._item_ids
        N = len(item_ids)

        sum_xi = self.X[self.item_id_to_index[item_ids[0]]]
        for id in item_ids[1:]:
            sum_xi = sum_xi + self.X[self.item_id_to_index[id]]

        alpha_bar = self.alpha + sum_xi
        beta_bar = self.beta + N - sum_xi
        log_alpha_bar = scipy.log(alpha_bar)
        log_beta_bar = scipy.log(beta_bar)

        self.c = (self.alpha_plus_beta - scipy.log(self.alpha_plus_beta + N)
            + log_beta_bar - self.log_beta).sum()
        self.q = log_alpha_bar - self.log_alpha - log_beta_bar + self.log_beta

    @utils.show_time_taken
    def _compute_scores(self):
        scores = self.X * self.q.transpose()
        scores = scipy.asarray(scores).flatten()
        self.log_scores = self.c + scores

    @utils.show_time_taken
    def _order_indexes_by_scores(self, max_results=100):
        if max_results == -1:
            self.ordered_indexes = xrange(len(self.log_scores))
        else:
            self.ordered_indexes = utils.argsort_best(self.log_scores, max_results, reverse=True)
            logger.info('Got %s indexes ...', len(self.ordered_indexes))

    @utils.show_time_taken
    def _compute_detailed_scores(self, item_ids, query_item_ids=None, max_terms=20):
        # if set to None we assume previously queried items
        if query_item_ids is None:
            query_item_ids = self.item_ids

        # if the query vector is different than previously computed
        # or not computed at all, we need to recompute it.
        if not hasattr(self, 'q') or query_item_ids != self.item_ids:
            if not self.is_valid_query(query_item_ids):
                return []
            else:
                logger.info('Computing the query vector ...')
                self._make_query_vector()

        # computing the score for each item
        scores = []
        for id in item_ids:
            if id not in self.item_id_to_index:
                scores.append(utils._O(total_score=0, scores=[]))
                continue

            xi = self.X[self.item_id_to_index[id]]
            xi_ind = xi.indices
            
            feat = (self.index_to_feat[i] for i in xi_ind)
            
            qi = self.q.transpose()[xi_ind]
            qi = scipy.asarray(qi).flatten()

            sc = sorted(zip(feat, qi), key=lambda x: (x[1], x[0]), reverse=True)
            total_score = qi.sum()
            scores.append(utils._O(total_score=total_score, scores=sc[0:max_terms]))

        return scores

    def _update_time_taken(self, reset=False):
        self.time = (
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
            time = self.time,
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
        s = 'You looked for item ids (after cleaning up): %s \n' % ', '.join(map(str, self._query_item_ids))
        s += 'Found %s in %.2f sec. (showing top 10 here):\n' % (self.total_found, self.time)
        s += '\n'.join('id = %s, log score = %s' % (id, log_score)
            for id, log_score in self.log_scores[0:10])
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


def search(index_path, item_ids):
    """Load the index and then query it against the item ids.
    """
    index = ComputedIndex(index_path)
    return QueryHandler(index).query(item_ids)


def load_index(index_path, pickled=False):
    """Loads a computed index given the path to an index.
    
    If pickled is true, load from a pickled computed index file.
    """
    if pickled:
        index = ComputedIndex.load(index_path)
    else:
        index = ComputedIndex(index_path)
    return index
    

def query_index(item_ids, computed_index, max_results=100):
    """Queries a computed index against the item ids.
    """
    return QueryHandler(computed_index).query(item_ids, max_results)
