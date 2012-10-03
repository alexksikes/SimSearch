Download and extract the latest tarball and install the package:

    wget http://github.com/alexksikes/SimSearch/tarball/master
    tar xvzf "the tar ball"
    cd "the tar ball"
    python setup.py install

You will need [SciPy][1] which is used for sparse matrix multiplications. To combine full text search with similarity search, you will need [Sphinx][2] and
[fSphinx][3].

Installing fSphinx and Sphinx is pretty straight forward. On linux (debian) to install scipy, you may need the following libraries:

sudo aptitude install libamd2.2.0 libblas3gf libc6 libgcc1 libgfortran3 liblapack3gf libumfpack5.4.0 libstdc++6 build-essential gfortran libatlas-base-dev python-all-dev

Finally you can install scipy:

pip install numpy
pip install scipy

[1]: http://www.scipy.org/
[2]: http://sphinxsearch.com/docs/manual-2.0.1.html#installation
[3]: http://github.com/alexksikes/fSphinx/
