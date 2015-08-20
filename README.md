Stable Matching Suite: Tools for Solving Generalized Stable Matching Problems  
==================================================================  

Authors: Fahiem Bacchus, Joanna Drummond, Andrew Perrault

Related Paper: http://ijcai.org/papers15/Papers/IJCAI15-079.pdf

Contents  
==================================================================  

1. smp_c.py: formulate a Stable Matching with Couples problem as a satisfiability problem (SAT) or as a mixed-integer program (MIP).
2. RPmatcher/matchrp: solve Stable Matching with Couples problems using deferred acceptance algorithms.
3. RPmatcher/matchvf: verify Stable Matching with Couples solutions.
4. rim.py: sample from Mallows ranking distributions.
5. cplex_py.py: interface with cplex.


Input Problem Format (Matching with Couples)
==================================================================  

The matchers are given a problem specification file. The lines of this
file each specify one bit of information about the matching
problem. The particular information they specify is determined by the
first character of the line. The information cannot extend over more
than one line.

Starting Character     Meaning  
blank or #             comment line ignored  
r                      resident specification line  
c                      couple specification line  
p                      program specification line  
anything else          error  

All residents/couples and programs are specified by ID (RIDs, CIDs and PIDs). These are integers >= 0.

r line  
-----  
"r rid rol"  
where rid is the resident id and rol is a sequence of program ids (pids). The order these pids occur is the rank ordering of these programs for resident rid (most prefered programs appear first).

c line  
------  
"c cid rid1 rid2 rol"  
where cid is the couple id, rid1 and rid2 are the resident ids of the first and second members of the couple. Note that rid1 and rid2 CANNOT appear in other "r" lines---"r" lines are for single residents. "rol" is a sequence of PIDs. There should be an even number of these. Each pair in this sequence pid1 pid2 ranks the matching where rid1 goes to pid1 and rid2 goes to pid2.

p line  
------  
"p pid quota rol"  
where pid is the program id, quota is the program's quota (integer >= 0) and rol is an ordered sequence of resident ids. 


Output Matching Format  
==================================================================

The matching file format has lines each of which specifies one bit of
information about the match. The particular information they specify
is determined by the first character of the line. The information
cannot extend over more than one line.

Starting Character     Meaning  
blank or #             comment line ignored  
r                      resident match line  
m                      match valid line (optional)  

m line  
------  
"m [0/1]"

If 1 then the file should contain a valid match. This allows the
matcher more gracefully handle a time out or detect a cycle: it can
fail to output a matching file. (If the match file is empty "m 0" is
implicit). In these cases the matcher is asserting that it could not
find a match. 

When it does find a match it should place a "m 1" line in the match
file. This asserts it found a match, now the verifier can check that
the match is correct. 

r line  
------  
"r rid pid"

Resident rid is matched to program pid.