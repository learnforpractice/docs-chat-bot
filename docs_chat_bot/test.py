import heapq


def largest_n_numbers(lst, n):
    if n > len(lst):
        return "n is larger than the length of the list"

    min_heap = []
    for num in lst:
        heapq.heappush(min_heap, num)
        if len(min_heap) > n:
            heapq.heappop(min_heap)

    return list(min_heap)

def largest_n_numbers_2(lst, n):
    if n > len(lst):
        raise Exception("n is larger than the length of the list")

    top_n = [float('-inf')] * n

    for num in lst:
        min_value = min(top_n)
        min_index = top_n.index(min_value)
        
        if num > min_value:
            top_n[min_index] = num

    return top_n

import random

my_list = [1, 5, 8, 9, 2, 0, 11, 23, 56, 42, 77]
my_list = [random.random() * 1000 for i in range(10000000)]
n = 4
import time

start = time.time()
result = largest_n_numbers(my_list, n)
print('+++duration:', time.time() - start)
print(sorted(result, reverse=True))

print('-'*10)
start = time.time()
sorted_list = sorted(my_list, reverse=True)
print("+++duration:", time.time() - start)
print(sorted_list[:n])


start = time.time()
ret = largest_n_numbers_2(my_list, n)
print("+++duration:", time.time() - start)
print(ret)
