"""[rim.py]
Copyright (c) 2014, Andrew Perrault, Joanna Drummond

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import numpy
import random
import sys


def rim_sample(ref_ranking, parameters, debug=False):
    sample = []
    sample.append(ref_ranking[0])
    for i in range(1, len(ref_ranking)):
        sample.insert(numpy.nonzero(
            numpy.random.multinomial(n=1, pvals=parameters[i]))[0],
            ref_ranking[i])
    return sample


def gen_dispersion_list(ref_ranking, dispersion, debug=False):
    print "generating dispersion list, finished: ",
    sys.stdout.flush()
    parameters = {}
    if dispersion == 0:
        return ref_ranking
    # have to translate to one-based indexing for the probabilities
    for i in range(2, len(ref_ranking) + 1):
        if i % 100 == 0:
            print i,
            sys.stdout.flush()
        sample_prob = numpy.zeros(i)
        for j in range(1, i + 1):
            if dispersion == 1:
                sample_prob[j - 1] = 1.0 / i
            else:
                sample_prob[j - 1] = (dispersion ** (i - j) *
                    (1 - dispersion) / (1 - dispersion ** i))
        if debug:
            assert sum(sample_prob) == 1
        parameters[i - 1] = sample_prob
    print "finished generating."
    return parameters


def mallows_sample(ref_ranking, dispersion_list, debug=False):
    return rim_sample(ref_ranking=ref_ranking, parameters=dispersion_list, debug=debug)


def mallows_sample_only_phi(ref_ranking, dispersion, debug=False):
    parameters = {}
    if dispersion == 0:
        return ref_ranking
    # have to translate to one-based indexing for the probabilities
    for i in range(2, len(ref_ranking) + 1):
        sample_prob = numpy.zeros(i)
        for j in range(1, i + 1):
            if dispersion == 1:
                sample_prob[j - 1] = 1.0 / i
            else:
                sample_prob[j - 1] = (dispersion ** (i - j) *
                    (1 - dispersion) / (1 - dispersion ** i))
        if debug:
            assert sum(sample_prob) == 1
        parameters[i - 1] = sample_prob
    return rim_sample(ref_ranking=ref_ranking,
        parameters=parameters, debug=debug)


def riffle_sample(ranking1, ranking2, sigma, debug=False):
    sample = []
    r1copy = list(ranking1)
    r2copy = list(ranking2)

    r1copy.reverse()
    r2copy.reverse()

    mixing_probability = max(min(random.gauss(0.25, sigma) if random.randint(0, 1)
        else random.gauss(0.75, sigma), 1.0), 0.0)
    for i in range(len(r1copy) + len(r2copy)):
        if len(r1copy) == 0 and len(r2copy) == 0:
            raise Exception('problem')
        if len(r1copy) == 0:
            sample.append(r2copy.pop())
            continue
        if len(r2copy) == 0 or random.random() <= mixing_probability:
            sample.append(r1copy.pop())
            continue
        sample.append(r2copy.pop())
    return sample
