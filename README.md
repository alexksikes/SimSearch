This module is an implementation of [Bayesian Sets][1]. Bayesian Sets is a new 
framework for information retrieval in which a query consists of a set of items 
which are examples of some concept. The result is a set of items which attempts 
to capture the example concept given by the query.

For example, for the query with the two animated movies, ["Lilo & Stitch" and "Up"][2], 
Bayesian Sets would return other similar animated movies, like "Toy Story".

This module also adds the novel ability to combine full text search with
item based search. For example a query can be a combination of items and full text search 
keywords. In this case the results match the keywords but are re-ranked by how similar 
to the queried items.

This implementation has been [tested][3] on datasets with millions of documents and 
hundreds of thousands of features. It has become an integrant part of [Cloud Mining][4]. 
At the moment only features of bag of words are supported. However it is faily easy 
to change the code to make it work on other feature types.

This module works as follow:

1) First a configuration file has to be written (have a look at tools/sample_config.py). 
The most important variable holds the list of features to index. Those are indexed 
with SQL queries of the type:

    sql_features = ['select id as item_id, word as feature from table']

Note that id and word must be aliased as item_id and feature respectively.
    
2) Now use tools/index_features.py on the configuration file to index those features.

    python tools/index_features.py config.py

The indexer will create a computed index named index.dat in your working directory. 
A computed index is a pickled file with all its hyper parameters already computed and 
with the matrix in CSR format. 
   
3) You can now test this index:

    python tools/query_index.py index.dat

4) The script *query_index.py* will load the index in memory each time. In order to load it
only once, you can serve the index with some client/server code (see client_server code).
The index can also be loaded along side the web application. In [webpy][5] web.config 
dictionnary can be used for this purpose.

This module relies and [Sphinx][6] and [fSphinx][7] to perform the full-text and item based 
search combination. A regular sphinx client is wrapped together with a computed index,
and a function called *setup_sphinx* is called upon similarity search. 
This function resets the sphinx client if an item based query is encountered.

Here is an example of a *setup_sphinx* function:

    # this is only used for sim_sphinx (see doc)
    def sphinx_setup(cl):
        import sphinxapi
        
        # custom sorting function for the search
        # we always make sure highly ranked items with a log score are at the top.
        cl.SetSortMode(sphinxapi.SPH_SORT_EXPR, '@weight * log_score_attr')'
        
        # custom grouping function for the facets
        group_func = 'sum(log_score_attr)'
        
        # setup sorting and ordering of each facet 
        for f in cl.facets:
            # group by a custom function
            f.SetGroupFunc(group_func)

Note that the log_scores are found in the Sphinx attributes *log_score_attr*. It must be set 
to 1 and declared as a float in your Sphinx configuration file:

    # log_score_attr must be set to 1
    sql_query            = \
        select *,\
            1 as log_score_attr,\
        from table
    
    # log_score_attr will hold the log scores after item base search
    sql_attr_float = log_score_attr

There is a nice [blog post][8] about item based search with Bayesian Sets. Feel free to 
[read][8] through it.
    
That's it for the documentation. Have fun playing with item based search and don't forget
to leave [feedback][9].

[1]: http://www.gatsby.ucl.ac.uk/~heller/bsets.pdf
[2]: http://imdb.cloudmining.net/search?q=%28%40similar+1049413+url--c2%2Fc29a902a5426d4917c0ca2d72a769e5b--title--Up%29++%28%40similar+198781+url--0b%2F0b994b7d73e0ccfd928bd1dfb2d02ce3--title--Monsters%2C+Inc.%29
[3]: http://imdb.cloudmining.net
[4]: https://github.com/alexksikes/CloudMining
[5]: http://webpy.org/
[6]: http://sphinxsearch.com/
[7]: https://github.com/alexksikes/fSphinx
[8]: http://thenoisychannel.com/2010/04/04/guest-post-information-retrieval-using-a-bayesian-model-of-learning-and-generalization/
[9]: mailto:alex.ksikes@gmail.com&subject=SimSearch
