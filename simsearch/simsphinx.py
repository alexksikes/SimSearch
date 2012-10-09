"""Wraps a Sphinx client with similarity search functionalities."""

__all__ = ['SimClient', 'QuerySimilar', 'QueryTermSimilar']

# TODO:
# - we need to check caching again
# - see if some things can be simplified
# - printing the results ...
# - review tutorial

import re
import sys
import os
import sphinxapi

from fsphinx import queries, MultiFieldQuery, QueryTerm
from fsphinx import QueryParser, FSphinxClient, CacheIO
import bsets
import utils

class SimClient(object):
    """Creates a wrapped sphinx client together with a computed index.
    
    The computed index is queried if a similary search query is encoutered.
    In this case the the function sphinx_setup is called in order to reset 
    the wrapped sphinx client.
    
    The log_score of each item is found in the Sphinx attribute "log_score_attr". 
    It must be set to 1 and declared as a float in your Sphinx configuration file.
    """
    def __init__(self, cl=None, query_handler=None, sphinx_setup=None, **opts):
        # essential options
        self.Wrap(cl)
        if opts.get('index_path'):
            self.LoadIndex(opts['index_path'])
        else:
            self.query_handler = query_handler
        self.SetSphinxSetup(sphinx_setup)
        # other options
        self.max_items = opts.get('max_items', 1000)
        self.max_terms = opts.get('max_terms', 20)
        self.exclude_queried = opts.get('exclude_queried', True)
        self.allow_empty = opts.get('allow_empty', True)
        if self.allow_empty:
            QuerySimilar.ALLOW_EMPTY = True
        
    def __getattr__(self, name):
        return getattr(self.wrap_cl, name)

    def Wrap(self, cl):
        """Use this method to wrap the sphinx client.
        """
        self.wrap_cl = cl
        if getattr(cl, 'query_parser', None):
            user_sph_map = cl.query_parser.kwargs.get('user_sph_map', {})
        else:
            user_sph_map = {}
        self.query_parser = QueryParser(QuerySimilar, user_sph_map=user_sph_map)
        return self
        
    def LoadIndex(self, index_path):
        """Load the similarity search index in memory.
        """
        idx = bsets.load_index(index_path)
        self.query_handler = bsets.QueryHandler(idx)    
        
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
        """
        # parse the query which is assumed to be a string
        self.query = self.query_parser.Parse(query)
        
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
            
        return hits
            
    @CacheIO
    def DoSimQuery(self, item_ids):
        """Performs the actual simlarity search query.
        """
        return self.query_handler.query(item_ids, self.max_items)
    
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
        if self.exclude_queried:
            self.wrap_cl.SetFilter('@id', item_ids, exclude=True)
        
        # only hits with non zero log scores are considered if the query is empty
        if not self.query.sphinx and self.allow_empty:
            self.wrap_cl.SetFilterFloatRange('log_score_attr', 0.0, 1.0, exclude=True)
        
    def _AddStats(self, sphinx_results, sim_results):
        # add detailed scoring information
        scores = self._GetDetailedScores(sphinx_results['ids'])
        for scores, match in zip(scores, sphinx_results['matches']):
            match['attrs']['@sim_scores'] = scores
        # and other statitics
        sphinx_results['time_similarity'] = sim_results.time
    
    @CacheIO
    def _GetDetailedScores(self, ids):
        return self.query_handler.get_detailed_scores(ids, max_terms=self.max_terms)
        
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
            cl.query_handler = bsets.QueryHandler(self.query_handler.computed_index)
        return cl

    @classmethod
    def FromConfig(cls, path):
        """Creates a client from a config file.
        """
        # if path is a module
        if hasattr(path, '__file__'):
            path = os.path.splitext(path.__file__)[0] + '.py'
        
        for d in utils.get_all_sub_dirs(path)[::-1]:
            sys.path.insert(0, d)
        cf = {'sys':sys}; execfile(path, cf, cf)
        return SimClient(**cf)
        
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
