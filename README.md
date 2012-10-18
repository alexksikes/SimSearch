SimSearch is an item based retrieval engine which implements [Bayesian Sets][0]. Bayesian Sets is a new framework for information retrieval in which a query consists of a set of items which are examples of some concept. The result is a set of items which attempts to capture the example concept given by the query.

For example, for the query with the two animated movies, ["Lilo & Stitch" and "Up"][1], Bayesian Sets would return other similar animated movies like "Toy Story". There is a nice [blog post][2] about item based search with Bayesian Sets. Feel free to [read][2] through it.

This module also adds the novel ability to combine full text queries with items. For example a query can be a combination of items and full text search keywords. In this case the results match the keywords and are re-ranked by similary to the queried items.

It is important to note that Bayesian Sets does not care about the actual [feature][3] engineering. For example SimSearch implements a simple [bag of words][4] model. However other feature types are possible as long as they can be binarized. In this case you will need to create the index directly. The index is a set of files in a .xco and .yco format (more in the [tutorial][6]) that represents the presence of a feature value in a given item. So as long as you can create these files, SimSearch can read them and perform the matching.

SimSearch has been [tested][5] on datasets with millions of documents and hundreds of thousands of features. Future plans include distributed search and real time indexing. For more information, feel free please to follow the [tutorial][6].

[0]: http://www.gatsby.ucl.ac.uk/~heller/bsets.pdf
[1]: http://imdb.cloudmining.net/search?q=%28%40similar+1049413+url--c2%2Fc29a902a5426d4917c0ca2d72a769e5b--title--Up%29++%28%40similar+198781+url--0b%2F0b994b7d73e0ccfd928bd1dfb2d02ce3--title--Monsters%2C+Inc.%29
[2]: http://thenoisychannel.com/2010/04/04/guest-post-information-retrieval-using-a-bayesian-model-of-learning-and-generalization/
[3]: http://en.wikipedia.org/wiki/Feature_(machine_learning)
[4]: http://en.wikipedia.org/wiki/Bag_of_words
[5]: http://imdb.cloudmining.net
[6]: https://github.com/alexksikes/SimSearch/tree/master/tutorial/
