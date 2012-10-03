In this tutorial, we will show how to use SimSearch to find similar movies. The dataset is taken from a scrape of the top 400 movies found on IMDb. We assume the current working directory to be the "tutorial" directory. All the code samples can be found in the file "./test.py".

Loading the Data in the Database
--------------------------------

First thing we need is some data. The dataset in this example is the same as featured in the [fSphinx tutorial][0]. If you don't already have it, create a MySQL database called "fsphinx" with user and password "fsphinx".

In a MySQL shell type:

    create database fsphinx character set utf8;
    create user 'fsphinx'@'localhost' identified by 'fsphinx';
    grant ALL on fsphinx.* to 'fsphinx'@'localhost';

Now let's load the data into this database:

    mysql -u fsphinx -D fsphinx -p < ./sql/imdb_top400.data.sql

Creating the Index
------------------

In this toy example we will consider two movies to be similar if they share "specific" plot keywords. Let's first have a quick look at our movies. In a mysql shell type:

    use fsphinx;
    select imdb_id, title from titles limit 5;

    +---------+--------------------------+
    | imdb_id | title                    |
    +---------+--------------------------+
    |  111161 | The Shawshank Redemption |
    |   61811 | In the Heat of the Night |
    |  369702 | Mar adentro              |
    |   56172 | Lawrence of Arabia       |
    |  107048 | Groundhog Day            |
    +---------+--------------------------+

Now let's create an index and add some keywords of interest:

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

SimSearch has created 4 files called .xco, .yxo, .ids and .fts in ./data/sim-index/. The files .xco and .yco are the x and y coordinates of the binary matrix. This matrix represents the presence of a feature for a given item id. The file .ids keep track of the item ids with respect to their index in this matrix. The .fts keep track of the feature values. The line number of the file is the actual matrix index.

If we'd like to build a larger index from a database, we would use an indexer. Let's build an index of all the plot keywords found on IMDb for this database.

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

    2012-10-03 11:34:11,600 - INFO - SQL: select imdb_id, plot_keyword from plot_keywords
    2012-10-03 11:34:12,894 - INFO - Done processing the dataset.
    2012-10-03 11:34:12,894 - INFO - Number of items: 424
    2012-10-03 11:34:12,895 - INFO - Number of features: 13607
    2012-10-03 11:34:12,895 - INFO - 1.29 sec.

It is important to note that the bag of words iterator is just an example. The indexer can take any iterator as long as the couple (item\_id, feature\_value) is returned. The id must always be an integer and the feature_value is a unique string representation of that feature value. However please note that you do not need to use these tools. In fact if you can directly create the matrix in .xco and .yco format, SimSearch can read it and perform its magic. For example the matrix could represent user's preferences. In this case the matrix would be the coordinates (item\_id, user\_id) indicating that user_id liked item_id. In this case the items are thought to be similar if they share a set of users liking them (the "you may also like" Amazon feature ...).

Querying the Index
------------------

Now we are ready to query this index and understand why things match. At its core SimSearch performs a sparse matrix multiplication. For speed efficiency the matrix must be converted into [CSR][4] and loaded in memory. This computed index is then queried using QueryHandler object.

    # let's create a computed index from our file index
    index = simsearch.ComputedIndex('./data/sim-index/')

    # and a query handler to query it
    handler = simsearch.QueryHandler(index)

    # now let's see what is similar to "The Shawshank Redemption" (item id 111161)
    results = handler.query(111161)
    print results

    You looked for item ids (after cleaning up): 111161
    Found 100 in 0.00 sec. (showing top 10 here):
    id = 111161, log score = 18087.2975693
    id = 455275, log score = 17787.5833743
    id = 107207, log score = 17784.619186
    id = 367279, log score = 17782.0579555
    id = 804503, log score = 17780.7218639
    id = 795176, log score = 17779.8914104
    id = 290978, log score = 17777.6663835
    id = 51808, log score = 17777.0082114
    id = 861739, log score = 17776.2298019
    id = 55031, log score = 17776.1551032

SimSearch does not have a storage engine. Instead we have to query our database to see what these movies are:

    select imdb_id, title from titles where imdb_id in (111161,36868,120586,455275,117666,40746,118421,405508,318997,107207) order by field(imdb_id, 111161,36868,120586,455275,117666,40746,118421,405508,318997,107207);

    +---------+------------------------------+
    | imdb_id | title                        |
    +---------+------------------------------+
    |  111161 | The Shawshank Redemption     |
    |  455275 | Prison Break                 |
    |  107207 | In the Name of the Father    |
    |  367279 | Arrested Development         |
    |  804503 | Mad Men                      |
    |  795176 | Planet Earth                 |
    |  290978 | The Office                   |
    |   51808 | Kakushi-toride no san-akunin |
    |  861739 | Tropa de Elite               |
    |   55031 | Judgment at Nuremberg        |
    +---------+------------------------------+

Ok obvisouly it matched itself, but why did "Prison Break" and "In the Name of the Father" matched?

    # let's get detailed scores for the movie id 455275 and 107207
    scores = handler.get_detailed_scores([455275, 107207], max_terms=5)
    pprint(scores)

    [{'scores': [(u'Prison Break', 3.9889840465642745),
       (u'Prison Escape', 3.4431615807611875),
       (u'Prison Guard', 3.3141860046725258),
       (u'Jail', 1.906534983820483),
       (u'Prison', 1.8838747581358608)],
      'total_score': 7.2857111578648492},
    {'scores': [(u'Wrongful Imprisonment', 3.5927355935610334),
       (u'False Accusation', 2.6005086594980238),
       (u'Courtroom', 2.2857779746776647),
       (u'Prison', 1.8838747581358608),
       (u'Political Conflict', -0.4062528198464137)],
      'total_score': 4.3215228336074638}]

Of course things would be much more interesting if we could index all movies in IMDb and consider other feature types such as directors or actors or preference data.

Note that the query handler is not thread safe. It is mearly meant to be used once and thrown away after each new query. However the computed index is and should be loaded somewhere in memory so it can be reused for subsequent queries. Also note that SimSearch is not limited to single item queries, you can just as quickly perform multiple item queries. Care to know what the movies "Lilo & Stitch" and "Up" [have in common][1]?

Although this is a toy example, SimSearch has been shown to perform quite well on millions of documents each having hundreds of thousands of possible feature values. There are also future plans to implement distributed search as well as real time indexing.

Combining Full Text Search with Similarity Search
-------------------------------------------------

Ok this is rather interesting, however sometimes we'd like to combine full text with item based search. For example we'd like to search for specific keywords and order these results based on how similar they are to a given set of items. This is accomplished by using the simsphinx module. The full text search query is handled by [Sphinx][2] so a little bit of setting up is necessary first.

First you need to install [Sphinx][2] and [fSphinx][3].

After you have installed Sphinx, let it index data (assuming Sphinx indexer is in /user/local/sphinx/):

    /usr/local/sphinx/bin/indexer -c ./config/indexer.conf --all
    
And now let searchd serve the index:

    /usr/local/sphinx/bin/searchd -c ./config/indexer.conf
 
Note that the "indexer.conf" must have an attribute called "log_scores_attr" set to 1 and declared as a float.

    # log_score_attr must be set to 1
    sql_query            = \
        select *,\
            1 as log_score_attr,\
        from table
    
    # log_score_attr will hold the scores of the matching items
    sql_attr_float = log_score_attr

We are now ready to combine full text search with item based search.

    # creating a sphinx client to handle full text search
    cl = simsearch.SimClient(handler)

A SimClient really is an FSphincClient which itself is a SphinxClient.

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

On seeing the query term "@similar 111161", the client performs a similarity search and then sets the log_score_attr accordingly. Let's have a look at these results:

    # looking at the results with similarity search
    print results

    matches: (25/25 documents in 0.000 sec.)
    1. document=112691, weight=1618
        ...     
        @sim_scores=[(u'Wrongful Imprisonment', 3.5927355935610334), (u'Prison Escape', 3.4431615807611875), (u'Prison', 1.8838747581358608), (u'Window Washer', -0.4062528198464137), (u'Sheep Rustling', -0.4062528198464137)], release_date_attr=829119600, genre_attr=[3, 5, 6, 9, 19], log_score_attr=17772.2988281, nb_votes_attr=16397
            id=112691
            title=Wallace and Gromit in A Close Shave
    2. document=417299, weight=1586
        ...
        @sim_scores=[(u'Redemption', 1.8838747581358608), (u'Friendship', 0.9769153536905899), (u'Tribe', -0.4062528198464137), (u'Psychic Child', -0.4062528198464137), (u'Flying Animal', -0.4062528198464137)], release_date_attr=1108972800, genre_attr=[2, 3, 9, 10], log_score_attr=17771.71875, nb_votes_attr=10432
            id=417299
            title=Avatar: The Last Airbender
    3. document=198781, weight=1618
        ...
        @sim_scores=[(u'Redemption', 1.8838747581358608), (u'Friend', 1.5656352897757075), (u'Friendship', 0.9769153536905899), (u'Pig Latin', -0.4062528198464137), (u'Hazmat Suit', -0.4062528198464137)], release_date_attr=1016611200, genre_attr=[2, 3, 5, 9, 10], log_score_attr=17766.1152344, nb_votes_attr=99627
            id=198781
            title=Monsters, Inc.

Again note that a SimClient is not thread safe. It is mearly meant to be used once or sequentially after each each request. In a web application you will need to create a new client for each new request. You can use SimClient.Clone on each new request for this purpose or you can create a new client from a config file with SimClient.FromConfig.

That's pretty much it. I hope you'll enjoy using SimSearch and please don't forget to leave [feedback][5].

[0]: https://github.com/alexksikes/fSphinx/blob/master/tutorial/
[1]: http://imdb.cloudmining.net/search?q=%28%40similar+1049413+url--c2%2Fc29a902a5426d4917c0ca2d72a769e5b--title--Up%29++%28%40similar+198781+url--0b%2F0b994b7d73e0ccfd928bd1dfb2d02ce3--title--Monsters%2C+Inc.%29
[2]: http://sphinxsearch.com
[3]: https://github.com/alexksikes/fSphinx
[4]: http://en.wikipedia.org/wiki/Sparse_matrix#Compressed_sparse_row_.28CSR_or_CRS.29
[5]: https://mail.google.com/mail/?view=cm&fs=1&tf=1&to=alex.ksikes@gmail.com&su=SimSearch
