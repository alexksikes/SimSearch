import numpy as np
import sys
import time
import heapq
import bottleneck as bn

from simsearch import utils


def show_time_taken(func):
    def new(*args, **kw):
        start = time.time()
        res = func(*args, **kw)
        timed = time.time() - start
        utils.logger.info('%.2f sec.', timed)
        setattr(new, 'time_taken', timed)
        return res
    return new

@show_time_taken
def argsort(arr):
    arr.argsort(0)

@show_time_taken
def arg_nlargest(arr, n):
    return utils.arg_nlargest(arr, n)

@show_time_taken
def heapq_nlargest(arr, n):
    return heapq.nlargest(n, arr)

@show_time_taken
def bn_argpartsort(arr, n):
    return bn.argpartsort(arr, n)

def test(arr, n):
    print 'arg_nlargest ...'
    arg_nlargest(arr, n)
    
    # print 'heapq.nlargest ...'
    # heapq_nlargest(arr, n)
    
    # print 'argsort ...'
    # argsort(arr)

    print 'bottleneck.argpartsort ...'
    bn_argpartsort(arr, n)
    
def main(arr_size, k):
    print '-' * 80
    print 'Test with integers from 1 to %s.' % arr_size
    arr = np.array(xrange(arr_size))
    test(arr, k)

    print '-' * 80
    print 'Test with random array.'
    arr = np.random.sample(arr_size)
    test(arr, k)

    print '-' * 80
    print 'Test with array of all ones.'
    arr = np.ones(arr_size)
    test(arr, k)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print 'Usage: python %s size_array n' % sys.argv[0]
    else:
        main(*map(int, sys.argv[1:]))
