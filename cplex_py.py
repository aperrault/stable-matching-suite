"""[cplex_py.py]
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

import os


class UIDAllocator():
    last_uid = None

    def allocate_uid(self):
        if self.last_uid is None:
            self.last_uid = 0
        else:
            self.last_uid = self.last_uid + 1
        return self.last_uid


general_uidallocator = UIDAllocator()


def allocate_general_uid():
    return general_uidallocator.allocate_uid()


def parse_var(var):
    subsplit = var.split(',')
    parse = [subsplit[0][0:subsplit[0].find('_')],
            subsplit[0][subsplit[0].find('_') + 1:]]
    parse.extend(subsplit[1:])
    return parse


class CPLEXRenderable():
    def render(self):
        raise Exception('must override in subclass')


class Expression(CPLEXRenderable):
    def __init__(self, terms_list=None):
        self.terms_list = terms_list
        if self.terms_list is None:
            self.terms_list = []

    def __repr__(self):
        return "Expression(%s)" % repr(self.terms_list)

    def add_term(self, term):
        self.terms_list.append(term)

    def is_negative(self):
        return self.terms_list[0].is_negative()

    def render(self):
        string_list = []
        if len(self.terms_list) == 0:
            print "warning: expression with empty terms_list"
            return ''
        string_list.append(self.terms_list[0].render())
        for i in xrange(1, len(self.terms_list)):
            if self.terms_list[i].is_negative():
                string_list.append(' - %s' % self.terms_list[i].render_negation())
            else:
                string_list.append(' + %s' % self.terms_list[i].render())
        return ''.join(string_list)

    def render_negation(self):
        string_list = []
        string_list.append(self.terms_list[0].render_negation())
        for i in xrange(1, len(self.terms_list)):
            if self.terms_list[i].is_negative():
                string_list.append(' - %s' % self.terms_list[i].render_negation())
            else:
                string_list.append(' + %s' % self.terms_list[i].render())
        return ''.join(string_list)

    def negate(self):
        self.terms_list = [term.negate() for term in self.terms_list]
        return self


class Bound(CPLEXRenderable):
    def __init__(self, var, lb=None, ub=None):
        self.lb = lb
        self.var = var
        self.ub = ub
        assert self.lb or self.ub

    def render(self):
        if self.lb and self.ub:
            return '%s <= %s <= %s' % (self.lb.render(),
                self.var.render(), self.ub.render())
        elif self.lb:
            return '%s <= %s' % (self.lb.render(), self.var.render())
        return '%s <= %s' % (self.var.render(), self.ub.render())


class BoundsCollection(CPLEXRenderable):
    def __init__(self, bounds=None):
        self.bounds = bounds
        if bounds is None:
            self.bounds = []

    def render(self):
        return '\n'.join([bound.render() for bound in self.bounds])

    def add_bound(self, bound=None, lb=None, var=None, ub=None):
        if bound:
            assert isinstance(bound)
            self.bounds.append(bound)
        else:
            self.bounds.append(Bound(lb=lb, var=var, ub=ub))


class Constraint(CPLEXRenderable):
    def __init__(self, var_side, const_side, name=None):
        self.var_side = var_side
        self.const_side = const_side
        if name:
            self.name = name
        else:
            self.name = 'c%d' % allocate_general_uid()


class EqualityConstraint(Constraint):
    def render(self):
        return '%s: %s = %s' % (self.name, self.var_side.render(), self.const_side.render())


class InequalityConstraint(Constraint):
    def render(self):
        return '%s: %s <= %s' % (self.name, self.var_side.render(), self.const_side.render())


class CoeffVar(CPLEXRenderable):
    def __init__(self, coeff=None, var=None):
        self.coeff = coeff
        self.var = var
        assert self.coeff is not None or self.var is not None

    def __repr__(self):
        return "CoeffVar(%s, %s)" % (
            repr(self.coeff) if self.coeff is not None else "1.",
            repr(self.var) if self.var is not None else repr(None))

    def render(self):
        if self.var is not None and self.coeff is not None:
            return '%f %s' % (self.coeff, self.var)
        elif self.var is not None:
            return '%s' % self.var
        return '%f' % self.coeff

    def render_negation(self):
        if self.var and self.coeff:
            return '%f %s' % (-self.coeff, self.var)
        elif self.var:
            return '-%s' % self.var
        return '%f' % -self.coeff

    def is_negative(self):
        if self.var and not self.coeff:
            return False
        else:
            return self.coeff < 0

    def negate(self):
        if self.coeff is None:
            self.coeff = -1.
        else:
            self.coeff = -self.coeff
        return self


class Infinity(CPLEXRenderable):
    def __init__(self, negative=False):
        self.negative = negative

    def render(self):
        if self.negative:
            return '-inf'
        else:
            return '+inf'


class ConstraintsCollection(CPLEXRenderable):
    def __init__(self, constraints=None):
        self.constraints = constraints
        if constraints is None:
            self.constraints = []
        general_uidallocator.last_uid = None

    def render(self):
        return '\n'.join([constraint.render() for constraint in self.constraints])

    def add_constraint(self, constraint):
        self.constraints.append(constraint)

    def add_constraints(self, constraints):
        self.constraints.extend(constraints)


def generate_random_suffix(suffix):
    import random
    random_suffix = str(random.randint(0, 100000))
    if suffix is not None:
        random_suffix += str(suffix)
    return random_suffix


def solve_using_CPLEX(objective,
    filename=None, solutionname=None,
    constraints=None, bounds=None, binaries=None,
    minimize=False, maximize=False, suffix=None,
    clean_files=True, treememory="1e+75",
    run_solver=True, solver_path=None,
    problem_name='problem'):
    if filename is None or solutionname is None:
        random_suffix = generate_random_suffix(suffix)
    if filename is None:
        filename = '%s-%s.lp' % (problem_name, random_suffix)
        while os.path.isfile(filename):
            random_suffix = generate_random_suffix(suffix)
            filename = '%s-%s.lp' % (problem_name, random_suffix)
    if solutionname is None:
        solutionname = 'output%s' % (random_suffix)
    scriptname = 'script%s' % (random_suffix)
    with open(scriptname, 'w') as script:
        ## set some parameters before we solve things
        script.write('set\nmip\nlimits\ntreememory\n%s\n' % treememory)
        script.write('read %s\noptimize\ndisplay solution variables -\nquit' % filename)
    assert maximize or minimize
    assert not (maximize and minimize)
    with open(filename, 'w') as f:
        if maximize:
            f.write('Maximize\n')
        else:
            f.write('Minimize\n')
        f.write('obj: %s\n' % objective.render())
        if constraints:
            f.write('Subject To\n%s\n' % constraints.render())
        if bounds:
            f.write('Bounds\n%s\n' % bounds.render())
        if binaries:
            f.write('Binaries\n%s\n' % '\n'.join(binaries))
        f.write('End')
    if run_solver:
        os.system('%s < %s > %s'
            % (solver_path, scriptname, solutionname))
        vals = {}
        objective = None
        with open(solutionname, 'r') as f:
            lines = f.readlines()
            startofvars = 0
            for index, line in enumerate(lines):
                if 'Objective =' in line:
                    stripped = line.strip()
                    objective = float(stripped[stripped.find('Objective = ') + 12:])
                if 'Variable Name' in line:
                    startofvars = index + 1
                    break
            if not startofvars:
                return None, None
            lines = lines[startofvars:-1]
            for line in lines:
                split = line[:-1].split()
                if 'All other variables in the range' in line:
                    break
                try:
                    vals[split[0]] = float(split[1])
                except:
                    continue
        if clean_files:
            os.system('rm %s %s %s' % (filename, solutionname, scriptname))
        return objective, vals
    else:
        return None, None
