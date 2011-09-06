"""Wraps a Sphinx client with similarity search functionalities."""

__all__ = ['SimSphinxWrap', 'QuerySimilar', 'QueryTermSimilar']

import re
import sphinxapi

from fsphinx import MultiFieldQuery, QueryTerm, FSphinxClient
import bsets

class SimSphinxWrap(sphinxapi.SphinxClient):
    """Creates a wrapped sphinx client together with a computed index.
    
    The computed index is queried if a similary search query is encoutered.
    In this case the the function sphinx_setup is called in order to reset 
    the wrapped sphinx client.
    
    The log_score of each item is found in the Sphinx attribute "log_score_attr". 
    It must be set to 1 and declared as a float in your Sphinx configuration file.
    """
    def __init__(self, wrap_cl, computed_index, sphinx_setup=None, max_items=1000):
        self.wrap_cl = wrap_cl
        self.sim = bsets.QueryHandler(computed_index)
        self.sphinx_setup = sphinx_setup
        self._max_items = max_items
        
    def __getattr__(self, name):
        return getattr(self.wrap_cl, name)
    
    def SetMaxItems(self, max_items):
        """Set the maximum number of items to match.
        """
        self._max_items = max_items
    
    def SetSphinxSetup(self, setup):
        """Set the setup function which will be triggered in similarity search 
        on the sphinx client.
        
        This function takes a sphinx client and operates on it in order to
        change sorting mode or ranking etc ... 
        
        The Sphinx attribute "log_score_attr" holds each item log score.
        """
        self.sphinx_setup = setup
    
    def Query(self, query):
        """If the query has item ids perform a similarity search query otherwise
        perform a normal sphinx query.
        
        The query must be a QuerySimilar object.
        """
        # parse the query which is assumed to be a QuerySimilar
        self.ParseQuery(query)
        item_ids = self.query.GetItemIds()
        
        if item_ids:
            # perform similarity search on the set of query items
            results = self.DoSimQuery(item_ids)
            # setup the sphinx client with log scores
            self._SetupSphinxClient(item_ids, dict(results.log_scores))
        
        # perform the Sphinx query
        hits = self.DoSphinxQuery(self.query)
            
        if item_ids:
            # add the statistics to the matches
            self._AddStats(hits, results)
            
    def ParseQuery(self, query):
        if hasattr(self.wrap_cl, 'query_parser'):
            user_sph_map = self.wrap_cl.query_parser.user_sph_map
        else:
            user_sph_map = {}
        self.query = QuerySimilar(user_sph_map)
        self.query.Parse(query)
        
    def DoSimQuery(self, item_ids):
        """Performs the actual simlarity search query.
        """
        return self.sim.query(item_ids, self._max_items)
    
    def DoSphinxQuery(self, query):
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
        
    def _AddStats(self, sphinx_results, sim_results):
        # add detailed scoring information
        scores = self.sim.get_detailed_scores(sphinx_results['ids'])
        for scores, match in zip(scores, sphinx_results['matches']):
            match['@sim_scores'] = scores
        # and other statitics
        sphinx_results['time_similarity'] = sim_results.time 
        
class QueryTermSimilar(QueryTerm):
    """This is like an fSphinx multi-field query but with the representation of 
    a query for similar items.
    
    A query for a similar item uses the special field @similar followed by the
    item id and some extra terms.
    
    Here is an example of a query to look up for the author "Alex Ksikes" and
    the item similar to the item with id "1234". The variable "Machine Learing"
    is passed along. 
    
    (@author alex ksikes) (@similar 1234--title--"Machine Learning")
    """
    p_item_id = re.compile('\s*(\d+)(?:--)?')
    p_extra = re.compile('--(\w+)--([^@()-]+)', re.I|re.U)
    
    def __init__(self, status, term):
        QueryTerm.__init__(self, status, 'similar', term)
        self.item_id = QueryTermSimilar.p_item_id.search(term).group(1)
        self.extra = dict(QueryTermSimilar.p_extra.findall(term))
        
    def GetExtraStr(self):
        """Returns a string representation of the extra items.
        """    
        return '--'.join('%s--%s' % (k, v) for k, v in self.extra.items())
    
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
    def _AddQueryTerm(self, qt):
        if qt.user_field == 'similar':
            qt = QueryTermSimilar(qt.status, qt.term)
        MultiFieldQuery._AddQueryTerm(self, qt)
        
    def GetItemIds(self):
        """Returns the item ids of this query term.
        """
        return map(int, (qt.item_id for qt in self if qt.user_field == 'similar' 
            and qt.status in ('', '+')))
