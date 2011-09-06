# database parameters
db_params = dict(user='user', passwd='password', db='dbname')

# list of SQL queries to fetch the features from
sql_features = [
    'select id as item_id, word as feature from table',
    'select id as item_id, word as feature from table2',
    '...'
]

# path to read or save the index
index_path = './index.dat'

# maximum number of items to match
max_items = 10000

# this is only used for sim_sphinx (see doc)
def sphinx_setup(cl):
    # import sphinxapi
    
    # custom sorting function for the search
    # cl.SetSortMode(sphinxapi.SPH_SORT_EXPR, 'log_score_attr')
    
    # custom grouping function for the facets
    group_func = 'sum(log_score_attr)'
    
    # setup sorting and ordering of each facet 
    for f in cl.facets:
        f.SetGroupFunc(group_func)
