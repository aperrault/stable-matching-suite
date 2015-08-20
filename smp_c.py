#!/usr/bin/env python

"""[smp_c.py]
Copyright (c) 2014, Andrew Perrault

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


from __future__ import with_statement

import argparse
import cplex_py
import os
import string

resident_dict = {}
hospital_dict = {}
couple_dict = {}

NIL_HOSPITAL_UID = 999999
NIL_HOSPITAL_SYMBOL = "-1"
TREEMEM_LIM = "12000"


def combinations(iterable, r):
    # combinations('ABCD', 2) --> AB AC AD BC BD CD
    # combinations(range(4), 3) --> 012 013 023 123
    pool = tuple(iterable)
    n = len(pool)
    if r > n:
        return
    indices = range(r)
    yield tuple(pool[i] for i in indices)
    while True:
        for i in reversed(range(r)):
            if indices[i] != i + n - r:
                break
        else:
            return
        indices[i] += 1
        for j in range(i + 1, r):
            indices[j] = indices[j - 1] + 1
        yield tuple(pool[i] for i in indices)


def product(*args, **kwds):
    # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
    # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
    pools = map(tuple, args) * kwds.get('repeat', 1)
    result = [[]]
    for pool in pools:
        result = [x + [y] for x in result for y in pool]
    for prod in result:
        yield tuple(prod)


class UIDAllocator():
    def __init__(self, first_uid=None):
        self.last_uid = first_uid - 1

    def allocate_uid(self):
        if self.last_uid is None:
            self.last_uid = 0
        else:
            self.last_uid = self.last_uid + 1
        return self.last_uid


class PreferenceFunction():
    def get_all_dispreferred(self, uid):
        raise Exception('must override in subclass')

    def get_all_weakly_preferred(self, uid):
        raise Exception('must override in subclass')

    def get_ordering(self):
        raise Exception('must override in subclass')

    def get_rank(self, uid):
        raise Exception('must override in subclass')


class ListPreferenceFunction(PreferenceFunction):
    def __init__(self, internal_list):
        self.internal_list = internal_list

    # list assumed in decreasing preference order,
    # i.e., most preferred first
    def get_all_preferred(self, uid):
        preferred = []
        for agent in self.internal_list:
            if agent == uid:
                return preferred
            preferred.append(agent)
        raise Exception('uid not in preference list: %r; internal_list; %r' % (uid, self.internal_list))

    def get_all_dispreferred(self, uid):
        dispreferred = []
        for agent in reversed(self.internal_list):
            if agent == uid:
                return dispreferred
            dispreferred.append(agent)
        raise Exception('uid not in preference list')

    def get_all_weakly_preferred(self, uid):
        return self.get_all_preferred(uid=uid) + [uid]

    def get_ordering(self):
        return self.internal_list

    def get_rank(self, uid):
        return self.internal_list.index(uid)


class JointPreferenceFunction():
    def get_cardinality(self):
        raise Exception('must override in subclass')

    def get_all_dispreferred(self, assignment, indices):
        raise Exception('must override in subclass')

    def get_all_weakly_preferred(self, assignment, indices):
        raise Exception('must override in subclass')

    def get_ordering(self):
        raise Exception('must override in subclass')

    def get_rank(self, item):
        raise Exception('must override in subclass')


class ListJointPreferenceFunction(JointPreferenceFunction):
    def __init__(self, internal_list, cardinality):
        # list of tuples of size of joint agent
        self.internal_list = internal_list
        self.cardinality = cardinality

    def get_cardinality(self):
        return self.cardinality

    # indices are indices that must remained fixed
    def _check_suitability(self, assignment, to_test, indices):
        suitable = True
        for i, item in enumerate(to_test):
            if i in indices and to_test[i] != assignment[i]:
                suitable = False
                break
        return suitable

    def get_all_dispreferred(self, assignment, indices):
        dispreferred = []
        for a in reversed(self.internal_list):
            if a == assignment:
                return dispreferred
            if self._check_suitability(assignment=assignment,
                to_test=a, indices=indices):
                dispreferred.append(a)
        raise Exception('uid not in preference list')

    def get_all_weakly_preferred(self, assignment, indices):
        weakly_preferred = []
        for a in self.internal_list:
            if a == assignment:
                weakly_preferred.append(a)
                return weakly_preferred
            if self._check_suitability(assignment=assignment,
                to_test=a, indices=indices):
                weakly_preferred.append(a)
        raise Exception('uid not in preference list')

    def get_ordering(self):
        return self.internal_list

    def get_rank(self, item):
        return self.internal_list.index(item)


class Agent():
    def __init__(self, uid):
        self.uid = uid
        assert self.uid is not None

    def __hash__(self):
        return self.uid

    def __eq__(self, other):
        return self.uid == other.uid


class SinglePreferrer(Agent):
    def __init__(self, preference_function, uid):
        Agent.__init__(self, uid=uid)
        self.preference_function = preference_function

    def get_all_preferred(self, uid):
        return self.preference_function.get_all_preferred(uid=uid)

    def get_all_dispreferred(self, uid):
        return self.preference_function.get_all_dispreferred(uid=uid)

    def get_all_weakly_preferred(self, uid):
        return self.preference_function.get_all_weakly_preferred(uid=uid)

    def get_ordering(self):
        return self.preference_function.get_ordering()

    def get_rank(self, uid):
        return self.preference_function.get_rank(uid=uid)


class JointPreferrer(Agent):
    def __init__(self, preference_function, uid, residents):
        Agent.__init__(self, uid=uid)
        self.preference_function = preference_function
        assert isinstance(self.preference_function, JointPreferenceFunction)
        self.residents = residents
        assert (len(self.residents)
            == self.preference_function.get_cardinality())

    def get_all_preferred(self, assignment, indices):
        assert len(indices) <= self.size
        return self.preference_function.get_all_preferred(
            assignment=assignment, indices=indices)

    def get_all_dispreferred(self, assignment, indices):
        assert len(indices) <= self.size
        return self.preference_function.get_all_dispreferred(
            assignment=assignment, indices=indices)

    def get_all_weakly_preferred(self, assignment, indices):
        assert len(indices) <= self.size
        return self.preference_function.get_all_weakly_preferred(
            assignment=assignment, indices=indices)

    def get_ordering(self):
        return self.preference_function.get_ordering()

    def get_rank(self, item):
        return self.preference_function.get_rank(item=item)


class Hospital(SinglePreferrer):
    def __init__(self, preference_function, uid, capacity=None):
        SinglePreferrer.__init__(self,
            preference_function=preference_function, uid=uid)
        self.capacity = capacity
        if self.capacity is not None:
            assert isinstance(self.capacity, int)
        hospital_dict[self.uid] = self


class NilHospital(Hospital):
    def __init__(self):
        Hospital.__init__(self,
            preference_function=None, uid=NIL_HOSPITAL_UID)
        self.capacity = 10
        if self.capacity is not None:
            assert isinstance(self.capacity, int)
        hospital_dict[self.uid] = self

    def get_all_preferred(self, assignment):
        return []

    def get_all_weakly_preferred(self, assignment):
        return []


class Resident(SinglePreferrer):
    def __init__(self, uid, preference_function=None, couple=None):
        SinglePreferrer.__init__(self,
            preference_function=preference_function, uid=uid)
        resident_dict[self.uid] = self
        self.couple = couple


class Couple(JointPreferrer):
    def __init__(self, preference_function, uid, residents):
        JointPreferrer.__init__(self,
            preference_function=preference_function, uid=uid,
            residents=residents)
        self.residents = residents
        couple_dict[uid] = self
        for resident in self.residents:
            resident.couple = self
        r0_ranked = []
        r1_ranked = []
        for (h0, h1) in self.preference_function.get_ordering():
            r0_ranked.append(h0)
            r1_ranked.append(h1)
        self.ranked_hospitals = {}
        self.ranked_hospitals[self.residents[0]] = list(set(r0_ranked))
        self.ranked_hospitals[self.residents[1]] = list(set(r1_ranked))
        self.size = 2

    def get_other_member(self, member):
        assert member in self.residents
        for person in self.residents:
            if person != member:
                return person

    def get_ranked_hospitals(self, member=None):
        if member is None:
            return self.preference_function.get_ordering()
        return self.ranked_hospitals[member]


class DIMACSConstraint():
    def __init__(self, var_list):
        self.var_list = var_list
        assert len(self.var_list) > 0

    def render(self):
        raise Exception('must override in subclass')


class DIMACSClause(DIMACSConstraint):
    def __init__(self, var_list):
        DIMACSConstraint.__init__(self, var_list=var_list)

    def render(self):
        return ' '.join([str(var) for var in self.var_list]) + ' 0'


class ConstraintsBuffer():
    def __init__(self, filename):
        self.filename = filename
        with open(self.filename, 'w') as f:
            f.write('')
        self.buffer_list = []
        self.buffer_size = 5000

    def append(self, constraint):
        if len(self.buffer_list) < self.buffer_size:
            self.buffer_list.append(constraint)
        else:
            with open(self.filename, 'a') as f:
                for item in self.buffer_list:
                    f.write(item.render() + '\n')
                f.write(constraint.render() + '\n')
            self.buffer_list = []

    def flush(self, variable_registry=None):
        with open(self.filename, 'a') as f:
            for item in self.buffer_list:
                f.write(item.render() + '\n')
                if variable_registry is not None:
                    print ' '.join([
                        ('-' + variable_registry[abs(var)]
                            if var < 0 else variable_registry[abs(var)])
                        for var in item.var_list])
        self.buffer_list = []

NIL_HOSPITAL = NilHospital()


def load_matching_from_file(filename):
    matching = {}
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if len(line) == 0:
                continue
            if line.startswith('#'):
                continue
            split = line.split()
            if split[0] == 'r':
                if split[2] == NIL_HOSPITAL_SYMBOL:
                    matching[int(split[1])] = NIL_HOSPITAL_UID
                else:
                    matching[int(split[1])] = int(split[2])
    return matching


class ProblemInstance():
    def __init__(self, hospitals, singles, couples):
        self.hospitals = hospitals
        self.singles = singles
        self.couples = couples
        self.matching = {}

    @classmethod
    def from_file(cls, filename, append_nil=False):
        # does not check that all referred to programs and residents exist after problem is defined
        # does check for duplicate residents and programs
        resident_dict = {}
        hospital_dict = {}
        couple_dict = {}
        with open(filename, 'r') as f:
            hospitals = []
            singles = []
            couples = []
            for line in f:
                if line.startswith('#') or line.startswith(' ') or line.startswith('\n') or line.startswith('\r'):
                    continue
                items = line.strip().split()
                if line.startswith('r'):
                    if int(items[1]) in resident_dict:
                        raise Exception('duplicate resident: %d' % int(items[1]))
                    rol = []
                    for i in xrange(2, len(items)):
                        rol.append(int(items[i]))
                    ## APPENDING nil so that when loading the match in for comparison purposes, we have a rank spot for the nil hospital
                    if append_nil:
                        if rol[-1] == int(NIL_HOSPITAL_SYMBOL):
                            rol.pop()
                        if rol[-1] != NIL_HOSPITAL_UID:
                            rol.append(NIL_HOSPITAL_UID)

                    s = Resident(uid=int(items[1]),
                        preference_function=ListPreferenceFunction(internal_list=rol))
                    singles.append(s)
                elif line.startswith('p'):
                    if int(items[1]) in hospital_dict:
                        raise Exception('duplicate program: %d' % int(items[1]))
                    rol = []
                    for i in xrange(3, len(items)):
                        rol.append(int(items[i]))
                    h = Hospital(uid=int(items[1]),
                        preference_function=ListPreferenceFunction(internal_list=rol),
                        capacity=int(items[2]))
                    hospitals.append(h)
                elif line.startswith('c'):
                    if int(items[1]) in couple_dict:
                        raise Exception('duplicate couple: %d' % int(items[1]))
                    if int(items[2]) in resident_dict:
                        raise Exception('resident in couple %d already defined: %d' % (int(items[1]), int(items[2])))
                    if int(items[3]) in resident_dict:
                        raise Exception('resident in couple %d already defined: %d' % (int(items[1]), int(items[3])))
                    rol = []
                    for i in xrange(4, len(items)):
                        if i % 2 != 0:
                            continue
                        rol.append((int(items[i]) if items[i] != NIL_HOSPITAL_SYMBOL else NIL_HOSPITAL_UID, int(items[i + 1]) if items[i + 1] != NIL_HOSPITAL_SYMBOL else NIL_HOSPITAL_UID))

                    ## APPENDING nil so that when loading the match in for comparison purposes, we have a rank spot for the nil hospital
                    if append_nil:
                        if rol[-1] != (NIL_HOSPITAL_UID, NIL_HOSPITAL_UID):
                            rol.append((NIL_HOSPITAL_UID, NIL_HOSPITAL_UID))

                    r0 = Resident(uid=int(items[2]))
                    r1 = Resident(uid=int(items[3]))
                    c = Couple(uid=int(items[1]),
                        preference_function=ListJointPreferenceFunction(internal_list=rol, cardinality=2),
                        residents=[r0, r1])
                    couples.append(c)
                else:
                    raise Exception('line not readable: %s' % line)
            return cls(hospitals=hospitals, singles=singles, couples=couples)

    # a matching here is just a dictionary from resident_uid -> program_uid
    @staticmethod
    def print_matching(matching, filename, header=None):
        with open(filename, 'w') as f:
            if header is not None:
                f.write('# %s\n' % header)
            if len(matching) == 0:
                f.write('m 0\n')
                return
            f.write('m 1\n')
            for resident_uid in matching.keys():
                if matching[resident_uid] == NIL_HOSPITAL_UID:
                    f.write('r %d %s\n' % (resident_uid, NIL_HOSPITAL_SYMBOL))
                else:
                    f.write('r %d %d\n' % (resident_uid, matching[resident_uid]))

    def solve_mip(self, solver, verbose=False, verify_file=None, run_solver=True,
                  problem_name='problem', output_filename=None):
        constraints = cplex_py.ConstraintsCollection()
        binaries = []

        def expand_match_var(resident, h, coeff=1.):
            if resident.couple is None:
                return [cplex_py.CoeffVar(coeff=coeff, var='x_%d,%d' % (resident.uid, h.uid))]
            else:
                if resident.couple.residents[0] == resident:
                    return [cplex_py.CoeffVar(coeff=coeff,
                            var=('x_%d,%d,%d' % (resident.couple.uid, h_uid_pair[0], h_uid_pair[1])))
                        for h_uid_pair in filter(
                            lambda x: x[0] == h.uid, resident.couple.get_ordering())]
                else:
                    return [cplex_py.CoeffVar(coeff=coeff,
                            var=('x_%d,%d,%d' % (resident.couple.uid, h_uid_pair[0], h_uid_pair[1])))
                        for h_uid_pair in filter(
                            lambda x: x[1] == h.uid, resident.couple.get_ordering())]

        # matching constraints
        for resident in self.singles:
            constraints.add_constraint(cplex_py.EqualityConstraint(
                var_side=cplex_py.Expression([cplex_py.CoeffVar(var='x_%d,%d' % (resident.uid, h_uid))
                    for h_uid in (resident.get_ordering() + [NIL_HOSPITAL_UID])]),
                const_side=cplex_py.CoeffVar(1.)))
            binaries.extend(['x_%d,%d' % (resident.uid, h_uid) for h_uid in (resident.get_ordering() + [NIL_HOSPITAL_UID])])
        for couple in self.couples:
            constraints.add_constraint(cplex_py.EqualityConstraint(
                var_side=cplex_py.Expression([cplex_py.CoeffVar(var='x_%d,%d,%d' % (couple.uid, h_uid_pair[0], h_uid_pair[1]))
                    for h_uid_pair in (couple.get_ordering() + [(NIL_HOSPITAL_UID, NIL_HOSPITAL_UID)])]),
                const_side=cplex_py.CoeffVar(1.)))
            binaries.extend(['x_%d,%d,%d' % (couple.uid, h_uid_pair[0], h_uid_pair[1])
                    for h_uid_pair in (couple.get_ordering() + [(NIL_HOSPITAL_UID, NIL_HOSPITAL_UID)])])
        for h in self.hospitals:
            var_side = []
            if len(h.get_ordering()) > 0:
                for resident_uid in h.get_ordering():
                    var_side.extend(expand_match_var(resident_dict[resident_uid], h))
                constraints.add_constraint(cplex_py.InequalityConstraint(
                    var_side=cplex_py.Expression(var_side), const_side=cplex_py.CoeffVar(h.capacity)))
        # stability constraints
        # singles
        for r in self.singles:
            ordering = r.get_ordering()
            for h_uid in ordering:
                h = hospital_dict[h_uid]
                var_side = []
                for r_prime in h.get_all_weakly_preferred(r.uid):
                    var_side.extend(expand_match_var(resident_dict[r_prime], h, coeff=-1.))
                constraints.add_constraint(cplex_py.InequalityConstraint(
                    var_side=cplex_py.Expression(var_side + [
                        cplex_py.CoeffVar(coeff=-h.capacity,
                            var='x_%d,%d' % (r.uid, p_prime_uid)) for p_prime_uid in r.get_all_weakly_preferred(h.uid)]),
                    const_side=cplex_py.CoeffVar(-h.capacity)))
        # one member of a couple
        for couple in self.couples:
            ordering = couple.get_ranked_hospitals()
            r0 = couple.residents[0]
            r1 = couple.residents[1]
            for number in xrange(len(ordering)):
                h0 = hospital_dict[ordering[number][0]]
                h1 = hospital_dict[ordering[number][1]]
                if not h0 == h1:
                    var_side = []
                    for r_prime in h0.get_all_weakly_preferred(r0.uid):
                        var_side.extend(expand_match_var(resident_dict[r_prime], h0, coeff=-1.))
                    constraints.add_constraint(cplex_py.InequalityConstraint(
                        var_side=cplex_py.Expression([cplex_py.CoeffVar(coeff=-h0.capacity,
                                    var='x_%d,%d,%d' % (couple.uid, h_prime_pair[0], h_prime_pair[1]))
                                   for h_prime_pair in couple.get_all_weakly_preferred((h0.uid, h1.uid), [])]
                                  + var_side
                                  + expand_match_var(r1, h1, coeff=h0.capacity)),
                        const_side=cplex_py.CoeffVar(0.)))
                    var_side = []
                    for r_prime in h1.get_all_weakly_preferred(r1.uid):
                        var_side.extend(expand_match_var(resident_dict[r_prime], h1, coeff=-1.))
                    constraints.add_constraint(cplex_py.InequalityConstraint(
                        var_side=cplex_py.Expression([cplex_py.CoeffVar(coeff=-h1.capacity,
                                    var='x_%d,%d,%d' % (couple.uid, h_prime_pair[0], h_prime_pair[1]))
                                   for h_prime_pair in couple.get_all_weakly_preferred((h0.uid, h1.uid), [])]
                                  + var_side
                                  + expand_match_var(r0, h0, coeff=h1.capacity)),
                        const_side=cplex_py.CoeffVar(0.)))
                else:
                    if h0.get_rank(r0.uid) < h0.get_rank(r1.uid):  # r0 preferred to r1
                        var_side = []
                        for r_prime in h1.get_all_weakly_preferred(r1.uid):
                            var_side.extend(expand_match_var(resident_dict[r_prime], h1, coeff=-1.))
                        constraints.add_constraint(cplex_py.InequalityConstraint(
                            var_side=cplex_py.Expression([cplex_py.CoeffVar(coeff=-h0.capacity,
                                        var='x_%d,%d,%d' % (couple.uid, h_prime_pair[0], h_prime_pair[1]))
                                       for h_prime_pair in couple.get_all_weakly_preferred((h0.uid, h1.uid), [])]
                                      + var_side
                                      + expand_match_var(r1, h1, coeff=h0.capacity)),
                            const_side=cplex_py.CoeffVar(0.)))
                        constraints.add_constraint(cplex_py.InequalityConstraint(
                            var_side=cplex_py.Expression([cplex_py.CoeffVar(coeff=-h1.capacity,
                                        var='x_%d,%d,%d' % (couple.uid, h_prime_pair[0], h_prime_pair[1]))
                                       for h_prime_pair in couple.get_all_weakly_preferred((h0.uid, h1.uid), [])]
                                      + var_side
                                      + expand_match_var(r0, h0, coeff=h1.capacity)),
                            const_side=cplex_py.CoeffVar(0.)))
                    else:
                        var_side = []
                        for r_prime in h0.get_all_weakly_preferred(r0.uid):
                            var_side.extend(expand_match_var(resident_dict[r_prime], h0, coeff=-1.))
                        constraints.add_constraint(cplex_py.InequalityConstraint(
                            var_side=cplex_py.Expression([cplex_py.CoeffVar(coeff=-h0.capacity,
                                        var='x_%d,%d,%d' % (couple.uid, h_prime_pair[0], h_prime_pair[1]))
                                       for h_prime_pair in couple.get_all_weakly_preferred((h0.uid, h1.uid), [])]
                                      + var_side
                                      + expand_match_var(r1, h1, coeff=h0.capacity)),
                            const_side=cplex_py.CoeffVar(0.)))
                        constraints.add_constraint(cplex_py.InequalityConstraint(
                            var_side=cplex_py.Expression([cplex_py.CoeffVar(coeff=-h1.capacity,
                                        var='x_%d,%d,%d' % (couple.uid, h_prime_pair[0], h_prime_pair[1]))
                                       for h_prime_pair in couple.get_all_weakly_preferred((h0.uid, h1.uid), [])]
                                      + var_side
                                      + expand_match_var(r0, h0, coeff=h1.capacity)),
                            const_side=cplex_py.CoeffVar(0.)))
            # also consider switch to (nil, nil)
            constraints.add_constraint(cplex_py.InequalityConstraint(
                var_side=cplex_py.Expression([cplex_py.CoeffVar(coeff=-1.,
                            var='x_%d,%d,%d' % (couple.uid, h_prime_pair[0], h_prime_pair[1]))
                           for h_prime_pair in couple.get_ordering() + [(NIL_HOSPITAL_UID, NIL_HOSPITAL_UID)]]
                          + expand_match_var(r1, NIL_HOSPITAL, coeff=1.)),
                const_side=cplex_py.CoeffVar(0.)))
            constraints.add_constraint(cplex_py.InequalityConstraint(
                var_side=cplex_py.Expression([cplex_py.CoeffVar(coeff=-1.,
                            var='x_%d,%d,%d' % (couple.uid, h_prime_pair[0], h_prime_pair[1]))
                           for h_prime_pair in couple.get_ordering() + [(NIL_HOSPITAL_UID, NIL_HOSPITAL_UID)]]
                          + expand_match_var(r0, NIL_HOSPITAL, coeff=1.)),
                const_side=cplex_py.CoeffVar(0.)))
        # both members of a couple switch
        for couple in self.couples:
            ordering = couple.get_ranked_hospitals()
            r0 = couple.residents[0]
            r1 = couple.residents[1]
            # need to find all hospitals that are ranked by the 2nd member of a couple
            # note: could generate fewer alpha variables if intelligent
            generated_alphas = {}
            for (h0_uid, h1_uid) in ordering:
                h0 = hospital_dict[h0_uid]
                h1 = hospital_dict[h1_uid]
                if (h0.capacity <= 1 or h0_uid == NIL_HOSPITAL_UID
                    or h1.capacity <= 1 or h1_uid == NIL_HOSPITAL_UID
                    or (r1.uid, h1_uid) in generated_alphas
                    or (r0.uid, h0_uid) in generated_alphas):
                    continue
                else:
                    binaries.append('alpha_%d,%d' % (r1.uid, h1_uid))
                    generated_alphas[(r1.uid, h1_uid)] = True
                    var_side = []
                    for r_prime in h1.get_all_weakly_preferred(r1.uid):
                        var_side.extend(expand_match_var(resident_dict[r_prime], h1, coeff=-1.))
                    constraints.add_constraint(cplex_py.InequalityConstraint(
                        var_side=cplex_py.Expression(var_side + [cplex_py.CoeffVar(coeff=h1.capacity, var='alpha_%d,%d' % (r1.uid, h1.uid))]),
                        const_side=cplex_py.CoeffVar(coeff=0.)))
            for number in xrange(len(ordering)):
                h0 = hospital_dict[ordering[number][0]]
                h1 = hospital_dict[ordering[number][1]]
                if h0.capacity == 0 or h1.capacity == 0:
                    continue
                if not h0 == h1:
                    var_side = []
                    if h1.uid != NIL_HOSPITAL_UID and h1.capacity > 1 and h0.uid != NIL_HOSPITAL_UID and h0.capacity > 1:
                        for r_prime in h0.get_all_weakly_preferred(r0.uid):
                            var_side.extend(expand_match_var(resident_dict[r_prime], h0, coeff=-1.))
                        constraints.add_constraint(cplex_py.InequalityConstraint(
                            var_side=cplex_py.Expression(expand_match_var(r0, h0, -h0.capacity)
                                      + expand_match_var(r1, h1, -h0.capacity)
                                      + [cplex_py.CoeffVar(coeff=-h0.capacity,
                                            var='x_%d,%d,%d' % (couple.uid, h_prime_pair[0], h_prime_pair[1]))
                                         for h_prime_pair in couple.get_all_weakly_preferred((h0.uid, h1.uid), [])]
                                      + var_side
                                      + [cplex_py.CoeffVar(coeff=-h0.capacity,
                                            var='alpha_%d,%d' % (r1.uid, h1.uid))]),
                            const_side=cplex_py.CoeffVar(-h0.capacity)))
                    elif h1.uid == NIL_HOSPITAL_UID or h1.capacity == 1:
                        for r_prime in h0.get_all_weakly_preferred(r0.uid):
                            var_side.extend(expand_match_var(resident_dict[r_prime], h0, coeff=-1.))
                        for r_prime in h1.get_all_weakly_preferred(r1.uid):
                            var_side.extend(expand_match_var(resident_dict[r_prime], h1, coeff=-h0.capacity))
                        constraints.add_constraint(cplex_py.InequalityConstraint(
                            var_side=cplex_py.Expression(expand_match_var(r0, h0, -h0.capacity)
                                      + expand_match_var(r1, h1, -h0.capacity)
                                      + [cplex_py.CoeffVar(coeff=-h0.capacity,
                                            var='x_%d,%d,%d' % (couple.uid, h_prime_pair[0], h_prime_pair[1]))
                                         for h_prime_pair in couple.get_all_weakly_preferred((h0.uid, h1.uid), [])]
                                      + var_side),
                            const_side=cplex_py.CoeffVar(-h0.capacity)))
                    elif h0.uid == NIL_HOSPITAL_UID or h0.capacity == 1:
                        for r_prime in h1.get_all_weakly_preferred(r1.uid):
                            var_side.extend(expand_match_var(resident_dict[r_prime], h1, coeff=-1.))
                        for r_prime in h0.get_all_weakly_preferred(r0.uid):
                            var_side.extend(expand_match_var(resident_dict[r_prime], h0, coeff=-h1.capacity))
                        constraints.add_constraint(cplex_py.InequalityConstraint(
                            var_side=cplex_py.Expression(expand_match_var(r0, h0, -h1.capacity)
                                      + expand_match_var(r1, h1, -h1.capacity)
                                      + [cplex_py.CoeffVar(coeff=-h1.capacity,
                                            var='x_%d,%d,%d' % (couple.uid, h_prime_pair[0], h_prime_pair[1]))
                                         for h_prime_pair in couple.get_all_weakly_preferred((h0.uid, h1.uid), [])]
                                      + var_side),
                            const_side=cplex_py.CoeffVar(-h1.capacity)))
                    else:
                        raise Exception('should never get here')
                else:
                    if h0.capacity == 1:
                        continue
                    var_side = []
                    if h0.get_rank(r0.uid) < h0.get_rank(r1.uid):  # r0 preferred to r1
                        for r_prime in h1.get_all_weakly_preferred(r1.uid):
                            var_side.extend(expand_match_var(resident_dict[r_prime], h1, coeff=-1.))
                    else:
                        for r_prime in h1.get_all_weakly_preferred(r0.uid):
                            var_side.extend(expand_match_var(resident_dict[r_prime], h0, coeff=-1.))
                    constraints.add_constraint(cplex_py.InequalityConstraint(
                        var_side=cplex_py.Expression(expand_match_var(r0, h0, -h0.capacity)
                                  + expand_match_var(r1, h1, -h0.capacity)
                                  + [cplex_py.CoeffVar(coeff=-h0.capacity,
                                        var='x_%d,%d,%d' % (couple.uid, h_prime_pair[0], h_prime_pair[1]))
                                     for h_prime_pair in couple.get_all_weakly_preferred((h0.uid, h1.uid), [])]
                                  + var_side),
                        const_side=cplex_py.CoeffVar(-h0.capacity + 1)))
        if verify_file is not None:
            r_match_dict = {}
            c_match_dict = {}
            h_match_dict = {}
            with open(verify_file, 'r') as f:
                for line in f:
                    if line.startswith('r '):
                        s = line.split()
                        h = hospital_dict[int(s[2])] if int(s[2]) != -1 else NIL_HOSPITAL
                        r = resident_dict[int(s[1])]
                        r_match_dict[r] = h
                        h_match_dict[h] = r

            for couple in self.couples:
                ordering = couple.get_ordering()
                r0 = couple.residents[0]
                r1 = couple.residents[1]
                c_match_dict[couple] = (r_match_dict[couple.residents[0]], r_match_dict[couple.residents[1]])

            def eval_cplex_constraint(constraint):
                if isinstance(constraint, cplex_py.InequalityConstraint):
                    total_left = 0
                    for var in constraint.var_side.terms_list:
                        if var.var.startswith('alpha'):
                            return (True, 0.0)
                        if var.var.startswith('x_'):
                            s = var.var.split(',')
                            s[0] = s[0][2:]
                            if len(s) == 3:
                                var_val = 1. if c_match_dict[couple_dict[int(s[0])]] == (hospital_dict[int(s[1])], hospital_dict[int(s[2])]) else 0.
                            else:
                                var_val = 1. if r_match_dict[resident_dict[int(s[0])]] == hospital_dict[int(s[1])] else 0.
                            total_left += var.coeff * var_val if var.coeff is not None else var_val
                    return ((total_left <= constraint.const_side.coeff), total_left)
                if isinstance(constraint, cplex_py.EqualityConstraint):
                    total_left = 0
                    for var in constraint.var_side.terms_list:
                        if var.var.startswith('alpha'):
                            return (True, 0.0)
                        if var.var.startswith('x_'):
                            s = var.var.split(',')
                            s[0] = s[0][2:]
                            if len(s) == 3:
                                var_val = 1. if c_match_dict[couple_dict[int(s[0])]] == (hospital_dict[int(s[1])], hospital_dict[int(s[2])]) else 0.
                            else:
                                var_val = 1. if r_match_dict[resident_dict[int(s[0])]] == hospital_dict[int(s[1])] else 0.
                            total_left += var.coeff * var_val if var.coeff is not None else var_val
                    return ((total_left == constraint.const_side.coeff), total_left)
            for constraint in constraints.constraints:
                if not eval_cplex_constraint(constraint)[0]:
                    print constraint.var_side
                    print constraint.const_side
                    print eval_cplex_constraint(constraint)[1]
            return
        if run_solver:
            (objective, vals) = cplex_py.solve_using_CPLEX(objective=cplex_py.Expression(terms_list=[cplex_py.CoeffVar(var=binaries[0])]),
                constraints=constraints, binaries=binaries, maximize=True, clean_files=True, treememory=TREEMEM_LIM, run_solver=run_solver,
                problem_name=problem_name, solver_path=solver)
        else:
            (objective, vals) = cplex_py.solve_using_CPLEX(objective=cplex_py.Expression(terms_list=[cplex_py.CoeffVar(var=binaries[0])]),
                constraints=constraints, binaries=binaries, maximize=True, clean_files=True, treememory=TREEMEM_LIM, run_solver=run_solver,
                problem_name=problem_name, solver_path=solver, filename=output_filename)
        if run_solver:
            if objective is None:
                return
            else:
                for val in vals:
                    if vals[val] == 1. and val.startswith('x_'):
                        s = val.split(',')
                        s[0] = s[0][2:]
                        if len(s) == 3:
                            couple = couple_dict[int(s[0])]
                            if int(s[1]) != NIL_HOSPITAL_UID:
                                self.matching[couple.residents[0].uid] = int(s[1])
                            if int(s[2]) != NIL_HOSPITAL_UID:
                                self.matching[couple.residents[1].uid] = int(s[2])
                        elif int(s[1]) != NIL_HOSPITAL_UID:
                            self.matching[int(s[0])] = int(s[1])

    def solve_sat(self, solver,
                  problem_name='problem',
                  verbose=False, verify_file=None, run_solver=True,
                  output_filename=None):
        if verbose:
            for single in self.singles:
                print 'Single %d prefs %s' % (single.uid, str(single.preference_function.internal_list))
            for couple in self.couples:
                print 'Couple %d prefs %s' % (couple.uid, str(couple.preference_function.internal_list))
                for resident in couple.residents:
                    print '    Resident %d' % (resident.uid)
            for hospital in self.hospitals:
                print 'Hospital %d capacity %d prefs %s' % (hospital.uid,
                    hospital.capacity if hospital.capacity is not None else -1,
                    str(hospital.preference_function.internal_list))

        variable_registry = {}
        import random
        random_suffix = random.randint(0, 100000)
        constraints_buffer_filename = 'constraints_buffer-%d' % (random_suffix)
        while os.path.isfile(constraints_buffer_filename):
            random_suffix = random.randint(0, 100000)
            constraints_buffer_filename = 'constraints_buffer-%d' % (random_suffix)
        if output_filename and not run_solver:
            solver_input_filename = output_filename
        else:
            solver_input_filename = '%s-%d.sat' % (problem_name, random_suffix)
        solver_output_filename = 'output-%d' % (random_suffix)
        constraints = ConstraintsBuffer(filename=constraints_buffer_filename)
        num_constraints = 0
        res_match = {}  # this will keep track of the DIMACS number of each matching variable
        var_uid_allocator = UIDAllocator(first_uid=1)

        # create numbers for all matching variables
        for resident in self.singles:
            assert not resident in res_match
            res_match[resident] = {}
            for hospital_uid in resident.get_ordering():
                hospital = hospital_dict[hospital_uid]
                res_match[resident][hospital] = \
                    var_uid_allocator.allocate_uid()
                variable_registry[res_match[resident][hospital]] = \
                    'xr_%d,%d' % (resident.uid, hospital.uid)
            res_match[resident][NIL_HOSPITAL] = var_uid_allocator.allocate_uid()
            variable_registry[res_match[resident][NIL_HOSPITAL]] = \
                'xr_%d,%d' % (resident.uid, NIL_HOSPITAL_UID)
            constraints.append(DIMACSClause([
                res_match[resident][hospital_dict[h_uid]] for h_uid in resident.get_ordering()]
                    + [res_match[resident][NIL_HOSPITAL]]))
        for couple in self.couples:
            for resident in couple.residents:
                assert not resident in res_match
                res_match[resident] = {}
                for h_uid in couple.get_ranked_hospitals(resident):
                    h = hospital_dict[h_uid]
                    res_match[resident][h] = \
                        var_uid_allocator.allocate_uid()
                    variable_registry[res_match[resident][h]] = \
                        'xc_%d,%d,%d' % (couple.uid, resident.uid, h_uid)
                # all residents that are members of a couple have a matching variable that represents the nil hospital
                res_match[resident][NIL_HOSPITAL] = var_uid_allocator.allocate_uid()
                variable_registry[res_match[resident][NIL_HOSPITAL]] = \
                    'xc_%d,%d,%d' % (couple.uid, resident.uid, NIL_HOSPITAL_UID)
                constraints.append(DIMACSClause([
                    res_match[resident][hospital_dict[h_uid]] for h_uid in couple.get_ranked_hospitals(resident)]
                        + [res_match[resident][NIL_HOSPITAL]]))
        # no resident can be assigned to two hospitals
        for resident in self.singles:
            for (h1_uid, h2_uid) in combinations(resident.get_ordering() + [NIL_HOSPITAL_UID], 2):
                constraints.append(DIMACSClause(
                    [-res_match[resident][hospital_dict[h1_uid]],
                     -res_match[resident][hospital_dict[h2_uid]]]))

        # no member of a couple can be assigned to two hospitals
        for couple in self.couples:
            for resident in couple.residents:
                for (h1_uid, h2_uid) in combinations(
                                            set(couple.get_ranked_hospitals(resident) +
                                            [NIL_HOSPITAL_UID]), 2):
                    constraints.append(DIMACSClause(
                        [-res_match[resident][hospital_dict[h1_uid]],
                         -res_match[resident][hospital_dict[h2_uid]]]))

        """
        counter variables
        q[program][number_counted][total]: after summing the number_counted most-preferred
            matching variables for program, the total was total
        q[program][0][0] is always True
        q[program][number_counted][program capacity + 1] is always False
        q[program][number_counted][> program capacity + 1] doesn't exist
        q[program][number_counted][> number_counted] doesn't exist
        """
        # expressed as q[h][i][j]
        q = {}
        for h in self.hospitals:
            q[h] = {}
            ordering = h.get_ordering()
            for i in xrange(len(ordering) + 1):
                if i == 0:
                    continue
                q[h][i] = {}
                for j in xrange(min(i + 1, h.capacity + 2)):
                    q[h][i][j] = var_uid_allocator.allocate_uid()
                    variable_registry[q[h][i][j]] = \
                        'q_%d,%d,%d' % (h.uid, i, j)
                if i == 1:
                    constraints.append(DIMACSClause(
                        [res_match[resident_dict[ordering[i - 1]]][h],
                         q[h][i][0]]))
                    constraints.append(DIMACSClause(
                        [-res_match[resident_dict[ordering[i - 1]]][h],
                         q[h][i][1]]))
                    constraints.append(DIMACSClause(
                        [-res_match[resident_dict[ordering[i - 1]]][h],
                         -q[h][i][0]]))
                    constraints.append(DIMACSClause(
                        [res_match[resident_dict[ordering[i - 1]]][h],
                         -q[h][i][1]]))
                else:
                    for j in xrange(min(i + 1, h.capacity + 2)):
                        if j == 0:
                            constraints.append(DIMACSClause(
                                [-res_match[resident_dict[ordering[i - 1]]][h],
                                 -q[h][i][0]]))
                            constraints.append(DIMACSClause(
                                [q[h][i - 1][0], -q[h][i][0]]))
                            constraints.append(DIMACSClause(
                                [res_match[resident_dict[ordering[i - 1]]][h],
                                 -q[h][i - 1][0], q[h][i][0]]))
                        elif j == i:
                            constraints.append(DIMACSClause(
                                [res_match[resident_dict[ordering[i - 1]]][h],
                                 -q[h][i][j]]))
                            constraints.append(DIMACSClause(
                                [q[h][i - 1][j - 1], -q[h][i][j]]))
                            constraints.append(DIMACSClause(
                                [-res_match[resident_dict[ordering[i - 1]]][h],
                                 -q[h][i - 1][j - 1], q[h][i][j]]))
                        else:
                            constraints.append(DIMACSClause(
                                [-res_match[resident_dict[ordering[i - 1]]][h],
                                 -q[h][i - 1][j - 1], q[h][i][j]]))
                            constraints.append(DIMACSClause(
                                [res_match[resident_dict[ordering[i - 1]]][h],
                                 -q[h][i - 1][j], q[h][i][j]]))
                            constraints.append(DIMACSClause(
                                [res_match[resident_dict[ordering[i - 1]]][h],
                                q[h][i - 1][j], -q[h][i][j]]))
                            constraints.append(DIMACSClause(
                                [-res_match[resident_dict[ordering[i - 1]]][h],
                                q[h][i - 1][j - 1], -q[h][i][j]]))
                # capacity constraints (assertions)
                if i >= h.capacity + 1:
                    constraints.append(DIMACSClause([-q[h][i][h.capacity + 1]]))

        """
        more auxiliary vars
        cpref[couple][rank] means couple is matched
            to rank or above pair of hospitals
        """
        cpref = {}
        for couple in self.couples:
            cpref[couple] = {}
            ordering = couple.get_ordering()
            for number in xrange(len(ordering)):
                h0 = hospital_dict[ordering[number][0]]
                h1 = hospital_dict[ordering[number][1]]
                cpref[couple][number] = var_uid_allocator.allocate_uid()
                variable_registry[cpref[couple][number]] = \
                    'cpref_%d,%d' % (couple.uid, number)
                if number == 0:
                    constraints.append(DIMACSClause(
                        [-cpref[couple][number],
                            res_match[couple.residents[0]][h0]]))
                    constraints.append(DIMACSClause(
                        [-cpref[couple][number],
                            res_match[couple.residents[1]][h1]]))
                    constraints.append(DIMACSClause(
                        [cpref[couple][number],
                            -res_match[couple.residents[0]][h0],
                            -res_match[couple.residents[1]][h1]]))
                else:
                    constraints.append(DIMACSClause(
                        [-cpref[couple][number],
                            cpref[couple][number - 1],
                            res_match[couple.residents[0]][h0]]))
                    constraints.append(DIMACSClause(
                        [-cpref[couple][number],
                            cpref[couple][number - 1],
                            res_match[couple.residents[1]][h1]]))
                    constraints.append(DIMACSClause(
                        [cpref[couple][number],
                            -cpref[couple][number - 1]]))
                    constraints.append(DIMACSClause(
                        [cpref[couple][number],
                            -res_match[couple.residents[0]][h0],
                            -res_match[couple.residents[1]][h1]]))

            # special cpref for couple is matched to (nil, nil)
            number = len(ordering)
            cpref[couple][number] = var_uid_allocator.allocate_uid()
            variable_registry[cpref[couple][number]] = \
                'cpref_%d,%d' % (couple.uid, number)
            constraints.append(DIMACSClause(
                [-cpref[couple][number],
                    cpref[couple][number - 1],
                    res_match[couple.residents[0]][NIL_HOSPITAL]]))
            constraints.append(DIMACSClause(
                [-cpref[couple][number],
                    cpref[couple][number - 1],
                    res_match[couple.residents[1]][NIL_HOSPITAL]]))
            constraints.append(DIMACSClause(
                [cpref[couple][number],
                    -cpref[couple][number - 1]]))
            constraints.append(DIMACSClause(
                [cpref[couple][number],
                    -res_match[couple.residents[0]][NIL_HOSPITAL],
                    -res_match[couple.residents[1]][NIL_HOSPITAL]]))

        # each couple must be matched to one of their ranked pairs or (nil, nil)
        for couple in self.couples:
            constraints.append(DIMACSClause(
                [cpref[couple][number] for number in xrange(len(couple.get_ordering()) + 1)]))

        def append_q_vars(l, q_vars):
            l_copy = list(l)
            for q_var in q_vars:
                (hospital, resident, number) = q_var
                if (not hospital == NIL_HOSPITAL
                    and hospital.get_rank(resident.uid) >= number):
                    l_copy.append(q[hospital][hospital.get_rank(resident.uid)][number])
            return l_copy

        # instability for singles
        for single in self.singles:
            for h_uid in single.get_ordering():
                h = hospital_dict[h_uid]
                constraints.append(DIMACSClause(
                    append_q_vars([res_match[single][hospital_dict[uid]] for uid in single.get_all_weakly_preferred(h_uid)],
                        [(h, single, h.capacity)])))

        # one member of a couple switches
        for couple in self.couples:
            ordering = couple.get_ranked_hospitals()
            r0 = couple.residents[0]
            r1 = couple.residents[1]
            for number in xrange(len(ordering)):
                h0 = hospital_dict[ordering[number][0]]
                h1 = hospital_dict[ordering[number][1]]
                if not h0 == h1:
                    constraints.append(DIMACSClause(
                        append_q_vars([-res_match[r1][h1], cpref[couple][number]],
                        [(h0, r0, h0.capacity)])))
                    constraints.append(DIMACSClause(
                        append_q_vars([-res_match[r0][h0], cpref[couple][number]],
                        [(h1, r1, h1.capacity)])))
                else:
                    if h0.get_rank(r0.uid) < h0.get_rank(r1.uid):
                        constraints.append(DIMACSClause(
                            append_q_vars([-res_match[r1][h1], cpref[couple][number]],
                            [(h0, r0, h0.capacity), (h1, r1, h1.capacity - 1)])))
                        constraints.append(DIMACSClause(
                            append_q_vars([-res_match[r0][h0], cpref[couple][number]],
                            [(h1, r1, h1.capacity)])))
                    else:
                        constraints.append(DIMACSClause(
                            append_q_vars([-res_match[r1][h1], cpref[couple][number]],
                            [(h0, r0, h0.capacity)])))
                        constraints.append(DIMACSClause(
                            append_q_vars([-res_match[r0][h0], cpref[couple][number]],
                            [(h0, r0, h0.capacity - 1), (h1, r1, h1.capacity)])))
            # also consider switch to (nil, nil)
            constraints.append(DIMACSClause([-res_match[r0][NIL_HOSPITAL],
                    cpref[couple][len(ordering)]]))
            constraints.append(DIMACSClause([-res_match[r1][NIL_HOSPITAL],
                    cpref[couple][len(ordering)]]))

        # both members of a couple switch
        for couple in self.couples:
            ordering = couple.get_ranked_hospitals()
            r0 = couple.residents[0]
            r1 = couple.residents[1]
            for number in xrange(len(ordering)):
                h0 = hospital_dict[ordering[number][0]]
                h1 = hospital_dict[ordering[number][1]]
                if h0.capacity == 0 or h1.capacity == 0:
                    continue
                if not h0 == h1:
                    constraints.append(DIMACSClause(
                        append_q_vars([res_match[r0][h0], res_match[r1][h1],
                            cpref[couple][number]],
                            [(h0, r0, h0.capacity), (h1, r1, h1.capacity)])))
                else:
                    if h0.capacity == 1:
                        continue
                    constraints.append(DIMACSClause(
                        append_q_vars([res_match[r0][h0], res_match[r1][h1],
                            cpref[couple][number]],
                            [(h0, r0, h0.capacity), (h1, r1, h1.capacity),
                             (h0, r0, h0.capacity - 1), (h1, r1, h1.capacity - 1)])))
            # also, consider switch to (nil, nil)
            constraints.append(DIMACSClause([res_match[r0][NIL_HOSPITAL], res_match[r1][NIL_HOSPITAL],
                    cpref[couple][len(ordering)]]))

        if verbose:
            constraints.flush(variable_registry=variable_registry)
        else:
            constraints.flush()
        # "lazy" implementation that only works in the one-to-one case
        # only fill out values of true variables
        if verify_file is not None:
            value_dict = {}
            h_hash = {}
            r_match_dict = {}
            with open(verify_file, 'r') as f:
                for line in f:
                    if line.startswith('r '):
                        s = line.split()
                        h = hospital_dict[int(s[2])]
                        r = resident_dict[int(s[1])]
                        value_dict[res_match[r][h]] = True
                        r_match_dict[r] = h
                        if h.uid != NIL_HOSPITAL_UID:
                            assert not h in h_hash
                            h_hash[h] = True
                            ordering = h.get_ordering()
                            found_match = False
                            for i in xrange(1, len(ordering) + 1):
                                if ordering[i - 1] == r.uid:
                                    value_dict[q[h][i][1]] = True
                                    found_match = True
                                    continue
                                if found_match:
                                    value_dict[q[h][i][1]] = True
                                else:
                                    value_dict[q[h][i][0]] = True
            for h in self.hospitals:
                if not h in h_hash:
                    ordering = h.get_ordering()
                    for i in xrange(1, len(ordering) + 1):
                        value_dict[q[h][i][0]] = True
            for couple in self.couples:
                ordering = couple.get_ordering()
                r0 = couple.residents[0]
                r1 = couple.residents[1]
                found_match = False
                if not r0 in r_match_dict:
                    r_match_dict[r0] = NIL_HOSPITAL
                    value_dict[res_match[r0][NIL_HOSPITAL]] = True
                if not r1 in r_match_dict:
                    r_match_dict[r1] = NIL_HOSPITAL
                    value_dict[res_match[r1][NIL_HOSPITAL]] = True
                for number in xrange(len(ordering)):
                    h0 = hospital_dict[ordering[number][0]]
                    h1 = hospital_dict[ordering[number][1]]
                    if h0 == r_match_dict[r0] and h1 == r_match_dict[r1]:
                        found_match = True
                    if found_match:
                        value_dict[cpref[couple][number]] = True
                value_dict[cpref[couple][len(ordering)]] = True

            def eval_str_clause(line):
                s = line.split()
                for number in s:
                    if int(number) == 0:
                        return False
                    if int(number) > 0 and int(number) in value_dict:
                        return True
                    if int(number) < 0 and not -int(number) in value_dict:
                        return True
            with open(constraints.filename, 'r') as f:
                for line in f:
                    if not eval_str_clause(line):
                        s = line.split()
                        print [variable_registry[int(x)] if int(x) > 0 else ("-" + variable_registry[-int(x)] if int(x) < 0 else None) for x in s]
            return
        constraints.flush()
        num_constraints = 0
        with open(constraints.filename, 'r') as f:
            for line in f:
                if all(c in string.whitespace for c in line):
                    continue
                num_constraints += 1
        with open(solver_input_filename, 'w') as problem:
            problem.write('p cnf %s %s\n' % (var_uid_allocator.last_uid, num_constraints))
            with open(constraints.filename, 'r') as f:
                for line in f:
                    if all(c in string.whitespace for c in line):
                        continue
                    problem.write(line)
        if run_solver:
            os.system('%s %s > %s' % (solver, solver_input_filename, solver_output_filename))
            if verbose:
                with open(solver_output_filename, 'r') as f:
                    for line in f:
                        s = line.split()
                        if len(s) == 1:
                            print s
                        else:
                            for var_str in s:
                                if var_str != '0':
                                    print '%s: %s' % (variable_registry[abs(int(var_str))],
                                        '1' if int(var_str) > 0 else '0')
            matching_found = True
            with open(solver_output_filename, 'r') as f:
                for line in f:
                    if "UNSATISFIABLE" in line:
                        matching_found = False
                        break
            if matching_found:
                self.matching = {}
                with open(solver_output_filename, 'r') as f:
                    for line in f:
                        if line.startswith('v'):
                            s = line.split()
                            for var_str in s[1:]:
                                if var_str != '0':
                                    var_name = variable_registry[abs(int(var_str))]
                                    if var_name.startswith('xr'):
                                        if int(var_str) > 0:
                                            self.matching[int(var_name[3:var_name.find(',')])] = int(
                                            var_name[var_name.find(',') + 1:len(var_name)])
                                    elif var_name.startswith('xc'):
                                        if int(var_str) > 0:
                                            self.matching[int(var_name.split(',')[1])] = int(var_name.split(',')[2])
                            for single in self.singles:
                                if not single.uid in self.matching:
                                    self.matching[single.uid] = NIL_HOSPITAL_UID
            assert not matching_found or self.matching
            os.system('rm %s %s' % (solver_input_filename, solver_output_filename))
        os.system('rm %s' % constraints_buffer_filename)


SUFFIX_TABLE = {
    'kpr': '.kpr_out',
    'rp99': '.rp99_out',
    'sat': '.satsolution',
    'mip': '.mipsolution'
}

FORMULATION_TABLE = {
    'sat': '.sat',
    'mip': '.lp'
}


def main():
    verbose = False
    output_filename = None
    run_solver = True
    parser = argparse.ArgumentParser()
    parser.add_argument('problem', help='the input problem file in the format described in the readme')
    parser.add_argument('-v', '--verbose', help='display more detail in problem formulation', action="store_true")
    parser.add_argument('--solver', help='the solver to be used: mip or sat', required=True, choices=['sat', 'mip'])
    parser.add_argument('--formulate', help='formulate, but do not solve, the problem', action="store_true")
    parser.add_argument('-o', '--output', help='output filename')
    args = parser.parse_args()
    if args.verbose:
        verbose = True
    if not args.output and not args.formulate:
        output_filename = args.problem + SUFFIX_TABLE[args.solver]
    elif not args.output and args.formulate:
        output_filename = args.problem + FORMULATION_TABLE[args.solver]
    else:
        output_filename = args.output
    if args.formulate:
        run_solver = False
    problem = ProblemInstance.from_file(args.problem)
    if args.solver == 'sat':
        solver_path = os.environ.get('SAT_SOLVER_PATH')
        if solver_path is None and run_solver:
            raise Exception('SAT_SOLVER_PATH must contain the path to a SAT solver that accepts the DIMACS input format')
        header = problem.solve_sat(solver=solver_path, verbose=verbose, run_solver=run_solver,
                                   problem_name=args.problem, output_filename=output_filename)
    elif args.solver == 'mip':
        solver_path = os.environ.get('CPLEX_PATH')
        if solver_path is None and run_solver:
            raise Exception('CPLEX_PATH must contain the path to CPLEX or another MIP solver that accepts CPLEX input')
        header = problem.solve_mip(solver=solver_path, verbose=verbose, run_solver=run_solver,
                                   problem_name=args.problem, output_filename=output_filename)
    if run_solver:
        ProblemInstance.print_matching(problem.matching,
            output_filename, header=header)

if __name__ == "__main__":
    main()
