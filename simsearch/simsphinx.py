"""Wraps a Sphinx client with similarity search functionalities."""

__all__ = ['SimSphinxWrap', 'QuerySimilar', 'QueryTermSimilar']

import re
import sphinxapi

from fsphinx import MultiFieldQuery, QueryTerm, QueryParser, FSphinxClient, \
    queries, CacheIO
import bsets

class SimSphinxWrap(sphinxapi.SphinxClient):
    """Creates a wrapped sphinx client together with a computed index.
    
    The computed index is queried if a similary search query is encoutered.
    In this case the the function sphinx_setup is called in order to reset 
    the wrapped sphinx client.
    
    The log_score of each item is found in the Sphinx attribute "log_score_attr". 
    It must be set to 1 and declared as a float in your Sphinx configuration file.
    """
    def __init__(self, computed_index, cl=None, sphinx_setup=None, max_items=1000):
        self.sim = bsets.QueryHandler(computed_index)
        self.sphinx_setup = sphinx_setup
        self.max_items = max_items
        self.query_parser = QueryParser(QuerySimilar)
        if cl:
            self.Wrap(cl)
        else:
            self.wrap_cl = None

    def __getattr__(self, name):
        return getattr(self.wrap_cl, name)
            
    def Wrap(self, cl):
        self.wrap_cl = cl
        if hasattr(cl, 'query_parser'): 
            user_sph_map = cl.query_parser.kwargs.get('user_sph_map', {}) 
        else:
            user_sph_map = {}
        self.query_parser = QueryParser(QuerySimilar, user_sph_map=user_sph_map)
        
        return self
        
    def SetMaxItems(self, max_items):
        """Set the maximum number of items to match.
        """
        self.max_items = max_items
    
    def SetSphinxSetup(self, setup):
        """Set the setup function which will be triggered in similarity search 
        on the sphinx client.
        
        This function takes a sphinx client and operates on it in order to
        change sorting mode or ranking etc ... 
        
        The Sphinx attribute "log_score_attr" holds each item log score.
        """
        self.sphinx_setup = setup
    
    def Query(self, query, index='*', comment=''):
        """If the query has item ids perform a similarity search query otherwise
        perform a normal sphinx query.
        """
        # parse the query which is assumed to be a string
        self.query = self.query_parser.Parse(query)
        self.time_similarity = 0
        
        item_ids = self.query.GetItemIds()
        if item_ids:
            # perform similarity search on the set of query items
            log_scores = self.DoSimQuery(item_ids)
            # setup the sphinx client with log scores
            self._SetupSphinxClient(item_ids, dict(log_scores))
        
        # perform the Sphinx query
        hits = self.DoSphinxQuery(self.query, index, comment)
        
        if item_ids:
            # add detailed scoring information
            self._AddStats(hits, item_ids)
        
        # and other statitics
        hits['time_similarity'] = self.time_similarity
        
        return hits
        
    @CacheIO
    def DoSimQuery(self, item_ids):
        """Performs the actual simlarity search query.
        """
        results = self.sim.query(item_ids, self.max_items)
        self.time_similarity = results.time
        
        return results.log_scores
        
    def DoSphinxQuery(self, query, index='*', comment=''):
        """Peforms a normal sphinx query.
        """
        if isinstance(self.wrap_cl, FSphinxClient):
            return self.wrap_cl.Query(query)
        else:
            # check we don't loose the parsed query
            return self.wrap_cl.Query(query.sphinx)
        
    def _SetupSphinxClient(self, item_ids, log_scores):
        # if the setup is in a configuration file
        if self.sphinx_setup:
            self.sphinx_setup(self.wrap_cl)
        
        # override log_score_attr and exclude selected ids
        self.wrap_cl.SetOverride('log_score_attr', sphinxapi.SPH_ATTR_FLOAT, log_scores)
        self.wrap_cl.SetFilter('@id', item_ids, exclude=True)
        
        # only hits with non zero log scores are considered if the query is empty
        QuerySimilar.ALLOW_EMPTY = True
        if not self.query.sphinx:
            self.wrap_cl.SetFilterFloatRange('log_score_attr', 0.0, 1.0, exclude=True)
    
    def _AddStats(self, sphinx_results, item_ids):
        scores = self._GetDetailedScores(item_ids, 
            [match['id'] for match in sphinx_results['matches']])
        for scores, match in zip(scores, sphinx_results['matches']):
            match['@sim_scores'] = scores
            
    @CacheIO
    def _GetDetailedScores(self, query_item_ids, result_ids, max_terms=20):
        scores = self.sim.get_detailed_scores(query_item_ids, result_ids, max_terms)
        self.time_similarity = scores.time
        
        return scores.scores
        
class QueryTermSimilar(QueryTerm):
    """This is like an fSphinx multi-field query but with the representation of 
    a query for similar items.
    
    A query for a similar item uses the special field @similar followed by the
    item id and some extra terms.
    
    Here is an example of a query to look up for the author "Alex Ksikes" and
    the item similar to the item with id "1234". The variable "Machine Learing"
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
