import numpy as np
import sys

from simsearch import utils


@utils.show_time_taken
def argsort(arr):
    arr.argsort(0)


@utils.show_time_taken
def argsort_best(arr, best_k, reverse=False):
    return utils.argsort_best(arr, best_k, reverse)
    

def test(arr, k):
    best_indexes = argsort_best(arr, k, reverse=True)

    print 'Array = %s' % arr
    print 'Best indexes = %s' % best_indexes
    print 'Best elements = %s' % arr[best_indexes]
    print 'Number of indexes = %s' % len(best_indexes)
    print 'Best element = %s' % np.max(arr)
    print 'Took %.2f sec.' % argsort_best.time_taken

    argsort(arr)
    print 'To be compared with full sorting takes %.2f sec.' % argsort.time_taken


def main(arr_size, k):
    arr = np.array(xrange(arr_size))
    test(arr, k)

    arr = np.random.sample(arr_size)
    test(arr, k)

    arr = np.ones(arr_size)
    test(arr, k)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print 'Usage: python %s size_array number_of_k_elements' % sys.argv[0]
    else:
        main(*map(int, sys.argv[1:]))
