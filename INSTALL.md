Download and extract the latest tarball and install the package:

    wget http://github.com/alexksikes/SimilaritySearch/tarball/master
    tar xvzf "the tar ball"
    cd "the tar ball"
    python setup.py install

You will need [NumPy][1] which is used for sparse matrix multiplications. 
To combine full text search with similarity search, you will need [Sphinx][2] and 
[fSphinx][3]. 

Enjoy!

[1]: http://numpy.scipy.org/
[2]: http://sphinxsearch.com/docs/manual-2.0.1.html#installation
[3]: http://github.com/alexksikes/fSphinx/
