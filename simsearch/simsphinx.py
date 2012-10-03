"""Wraps a Sphinx client with similarity search functionalities."""

__all__ = ['SimClient', 'QuerySimilar', 'QueryTermSimilar']

import utils
import re
import copy
import sphinxapi

from fsphinx import *

class SimClient(FSphinxClient):
    """Creates a wrapped sphinx client together with a computed index.

    The computed index is queried if a similarity search query is encountered.
    
    The log_score of each item is found in the Sphinx attribute "log_score_attr".
    It must be set to 1 and declared as a float in your Sphinx configuration file.
    """
    def __init__(self, query_handler=None, cl=None, **opts):
        FSphinxClient.__init__(self)
        # default query parser
        self.AttachQueryParser(QueryParser(QuerySimilar))
        # set the query handler for simsearch
        self.SetQueryHandler(query_handler)
        # default sorting function
        self.SetSortMode(sphinxapi.SPH_SORT_EXPR, 'log_score_attr')
        # initiate from an existing client
        if cl:
            self.SetSphinxClient(cl)
        # some default options
        self._max_items = opts.get('max_items', 1000)
        self._max_terms = opts.get('max_terms', 20)
        self._exclude_queried = opts.get('exclude_queried', True)
        self._allow_empty = opts.get('allow_empty', True)
        if self._allow_empty:
            QuerySimilar.ALLOW_EMPTY = True
        
    def SetSphinxClient(self, cl):
        """Use this method to wrap the sphinx client.
        """
        # prototype pattern, create based on existing instance
        self.__dict__.update(copy.deepcopy(cl).__dict__)
        if hasattr(cl, 'query_parser'):
            if hasattr(cl.query_parser, 'user_sph_map'):
                self.query_parser = QueryParser(
                    QuerySimilar, user_sph_map=cl.user_sph_map)
                
    def SetQueryHandler(self, query_handler):
        """Sets the query handler to perform the similarity search.
        """
        self.query_handler = query_handler

    def Query(self, query, index='', comment=''):
        """If the query has item ids perform a similarity search query otherwise
        perform a normal sphinx query.
        """
        # first let's parse the query if possible
        if isinstance(query, basestring):
            query = self.query_parser.Parse(query)
        self.query = query
        
        # now let's get the item ids
        item_ids = self.query.GetItemIds()
        if item_ids:
            # perform similarity search on the set of query items
            log_scores = self.DoSimQuery(item_ids)
            # setup the sphinx client with log scores
            self._SetupSphinxClient(item_ids, dict(log_scores))
        
        # perform the normal Sphinx query
        hits = FSphinxClient.Query(self, query, index, comment)
        
        # reset filters for subsequent queries
        self.ResetOverrides()
        self.ResetFilters()
        
        # add detailed scoring information to each match
        self._AddStats(item_ids)

        # keep expected return of SphinxClient
        return self.hits

    @CacheIO
    def DoSimQuery(self, item_ids):
        """Performs the actual similarity search query.
        """
        results = self.query_handler.query(item_ids, self._max_items)
        return results.log_scores
        
    def _SetupSphinxClient(self, item_ids, log_scores):
        # override the log_score_attr attributes with its value
        self.SetOverride('log_score_attr', sphinxapi.SPH_ATTR_FLOAT, log_scores)
        # exclude query item ids from results
        if self._exclude_queried:
            self.SetFilter('@id', item_ids, exclude=True)
        # allow full scan on empty query but restrict to non zero log scores
        if not self.query.sphinx and self._allow_empty:
            self.SetFilterFloatRange('log_score_attr', 0.0, 1.0, exclude=True)

    def _AddStats(self, query_item_ids):
        scores = []
        ids = [match['id'] for match in self.hits['matches']]
        if ids:
            scores = self._GetDetailedScores(ids, query_item_ids)
        for scores, match in zip(scores, self.hits['matches']):
            match['attrs']['@sim_scores'] = scores.scores
        self.hits['time_similarity'] = self.query_handler.time
        
    @CacheIO
    def _GetDetailedScores(self, ids, query_item_ids):
        return self.query_handler.get_detailed_scores(ids, query_item_ids, max_terms=self._max_terms)
        
    def Clone(self, memo={}):
        """Creates a copy of this client.

        This makes sure the whole index is not recopied.
        """
        return self.__deepcopy__(memo)

    def __deepcopy__(self, memo):
        cl = self.__class__()
        attrs = utils.save_attrs(self,
            [a for a in self.__dict__ if a not in ['query_handler']])
        utils.load_attrs(cl, attrs)
        if self.query_handler:
            computed_index = self.query_handler.computed_index
            cl.SetQueryHandler(QueryHandler(computed_index))
        return cl


class QueryTermSimilar(QueryTerm):
    """This is like an fSphinx multi-field query but with the representation of
    a query for similar items.

    A query for a similar item uses the special field @similar followed by the
    item id and some extra terms.

    Here is an example of a query to look up for the author "Alex Ksikes" and
    the item similar to the item with id "1234". The variable "Machine Learning"
    is passed along.

    (@author alex ksikes) (@similar 1234--"Machine Learning")
    """
    p_item_id = re.compile('\s*(\d+)(?:--)?')
    p_extra = re.compile('--(.+?)(?=--|$)', re.I|re.U)

    def __init__(self, status, term):
        QueryTerm.__init__(self, status, 'similar', term)
        self.item_id = QueryTermSimilar.p_item_id.search(term).group(1)
        self.extra = QueryTermSimilar.p_extra.findall(term)

    def GetExtraStr(self):
        """Returns a string representation of the extra items.
        """
        return '--'.join(self.extra.items())

    @property
    def sphinx(self):
        return ''

    @property
    def uniq(self):
        if self.status in ('', '+'):
            return '(@%s %s)' % (self.sph_field, self.item_id)
        else:
            return ''

#    def __cmp__(self, qt):
#        return cmp((self.user_field, self.item_id), (qt.user_field, qt.item_id))

    def __hash__(self):
        return hash((self.user_field, self.item_id))


class QuerySimilar(MultiFieldQuery):
    """Used internally by a query term similar query.

    These query terms may be created from a match object or its string representation.
    """
    @queries.ChangeQueryTerm
    def AddQueryTerm(self, query_term):
        if query_term.user_field == 'similar':
            query_term = QueryTermSimilar(query_term.status, query_term.term)
        MultiFieldQuery.AddQueryTerm(self, query_term)

    def GetItemIds(self):
        """Returns the item ids of this query term.
        """
        return map(int, (qt.item_id for qt in self if qt.user_field == 'similar'
            and qt.status in ('', '+')))
