Stable Matching Suite: Tools for Solving Generalized Stable Matching Problems
===========

Authors: Fahiem Bacchus, Joanna Drummond, Andrew Perrault

Related Paper: http://ijcai.org/papers15/Papers/IJCAI15-079.pdf

Contents:

1. smp_c.py: formulate a Stable Matching with Couples problem as a satisfiability problem (SAT) or as a mixed-integer program (MIP).
2. RPmatcher/matchrp: solve Stable Matching with Couples problems using deferred acceptance algorithms.
3. RPmatcher/matchvf: verify Stable Matching with Couples solutions.
4. rim.py: sample from Mallows ranking distributions.
5. cplex_py.py: interface with cplex.

Input format for Stable Matching with Couples instances:

Each resident, couple and program has a unique id. The file consists of three sections.
1. The first section describes residents and each line has the form:  
r rid pid0 pid1 ...
where rid is the resident's unique identifier and [pid0, pid1, ...] is the resident's ranking of programs.  
2. The second section describes couples. Each line has the form:  
c cid rid0 rid1 pid0a pid0b pid1a pid1b
where cid is the couple's unique identifier, rid0 and rid1 and the residents in the couple and [(pid0a, pid0b), (pid1a, pid1b), ...] is the couple's ranking of programs.  
3. The third section describes programs. Each line has the form:  
p pid cap rid0 rid1 ...
where pid is the program's unique identifier, cap is the program's capacity and [rid0, rid1, ...] is the program's ranking of residents.

Output format for matchings:

Output matchings have a first line which is either  
m 0  
or  
m 1.  
m 0 indicates no matching was found. m 1 indicates a matching was found and follows. The following lines have the form:  
r rid pid  
which indicates that resident rid was matched to program pid.
