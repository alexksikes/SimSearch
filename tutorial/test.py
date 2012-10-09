import simsearch
from pprint import pprint

# creating the index in './data/sim-index/'
index = simsearch.FileIndex('./data/sim-index', mode='write')

# adding some features for the item id 111161 and 107048
index.add(111161, 'prison')
index.add(111161, 'murder')
index.add(111161, 'shawshank')
index.add(107048, 'weatherman')
index.add(107048, 'weather forecasting')
index.close()

# let's create our index
index = simsearch.FileIndex('./data/sim-index', mode='write')

# our database parameters
db_params = {'user':'fsphinx', 'passwd':'fsphinx', 'db':'fsphinx'}

# an iterator to provide the indexer with (id, feature value)
bag_of_words_iter = simsearch.BagOfWordsIter(
    db_params = db_params, 
    sql_features = ['select imdb_id, plot_keyword from plot_keywords']
)

# create the index provisionned by our iterator
indexer = simsearch.Indexer(index, bag_of_words_iter)

# and finally index all the items in our database
indexer.index_data()

# let's create a computed index from our file index
index = simsearch.ComputedIndex('./data/sim-index/')

# and a query handler to query it
handler = simsearch.QueryHandler(index)

# now let's see what is similar to "The Shawshank Redemption" (item id 111161)
results = handler.query(111161)
print results

# let's get detailed scores for the movie id 455275 and 107207
scores = handler.get_detailed_scores([455275, 107207], max_terms=5)
pprint(scores)

print 'Combining Full Text Search with Similarity Search'
print '-------------------------------------------------'

import fsphinx
import sphinxapi

# creating a sphinx client to handle full text search
cl = simsearch.SimClient(fsphinx.FSphinxClient(), handler, max_terms=5)

# assuming searchd is running on 9315
cl.SetServer('localhost', 9315)

# telling fsphinx how to fetch the results
db = fsphinx.utils.database(dbn='mysql', **db_params)

cl.AttachDBFetch(fsphinx.DBFetch(db, sql=''' 
    select imdb_id as id, title 
    from titles 
    where imdb_id in ($id) 
    order by field(imdb_id, $id)'''
))

# order the results solely by similarity using the log_score_attr
cl.SetSortMode(sphinxapi.SPH_SORT_EXPR, 'log_score_attr')

# enable us to search within fields
cl.SetMatchMode(sphinxapi.SPH_MATCH_EXTENDED2)

# searching for all animation movies re-ranked by similarity to "The Shawshank Redemption"
results = cl.Query('@genres animation @similar 111161')

# looking at the results with similarity search
print results
