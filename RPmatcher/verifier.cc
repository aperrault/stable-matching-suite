/***********[Main.cc]
Copyright (c) 2014, Fahiem Bacchus

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

***********/

#include <vector>
#include <iostream>
#include <fstream>
#include <limits>
#include <algorithm>
#include <iterator>
#include <sstream>
#include <unordered_set>
#include <assert.h>
#include "minisat/utils/Options.h"

using std::vector;
using std::string;
using std::unordered_set;
using std::ostream;
using std::pair;
using std::cout;
using std::cerr;
using std::istringstream;
using std::ostringstream;

using Minisat::setUsageHelp;
using Minisat::IntOption;
using Minisat::IntRange;
using Minisat::BoolOption;
using Minisat::parseOptions;
using Minisat::printUsageAndExit;


//Data structures and classes.
//Use integer IDs to refer to residents/couples/programs.
//Use classes to contain information/functionality for these items.
//A problem is specfied by a vector of residents/couples/programs.
//integer IDs index into these vectors.

//Forward declarations
class Resident;
class Couple;
class Program;
class Problem;
class RID;
class PID;
class CID;
typedef pair<PID, PID> PIDPair;

class RID {
public: 
  int id;
  static Problem* prob;
  operator size_t() const { return static_cast<size_t>(id); }
  RID(int i) : id {i} {}
  RID() : id {} {}
  int rankOf(PID p) const;
  bool prefers(PID p1, PID p2) const;
  bool isRanked(PID p) const;
  bool willAccept(PID p) const;
  PID matchedTo() const;
  bool isMatched() const;
  void match(PID prog) const;
  void unmatch() const;
  bool inCouple() const;
  CID couple() const;
  RID partner() const;
  const vector<PID>& ROL() const;
};

ostream& operator<<(ostream& os, const RID& r) {
  os << r.id ;
  return os;
}

class PID {
public:
  int id;
  static Problem* prob;
  operator size_t() const { return static_cast<size_t>(id); }
  PID(int i) : id {i} {}
  PID() : id {} {}
  RID minRes() const;
  RID min2ndRes() const;
  int rankOf(RID r) const;
  bool prefers(RID r1, RID r2) const;
  bool isRanked(RID r) const;
  bool willAccept(RID r) const;
  bool willAccept(RID r1, RID r2) const;
  int nmatched() const;
  vector<RID> match(RID r) const;
  vector<RID> match(RID r1, RID r2) const;
  void unmatch(RID r) const;
  int QUOTA() const;
  const vector<RID>& ACCEPTED() const;
  const vector<RID>& ROL() const;
};

ostream& operator<<(ostream& os, const PID& p) {
  os << p.id ;
  return os;
}

class CID {
public:
  int id;
  static Problem* prob;
  operator size_t() const { return static_cast<size_t>(id); }
  CID(int i) : id {i} {}
  CID() : id {} {}
  int rankOf(PIDPair p) const;
  bool prefers(PIDPair p1, PIDPair p2) const;
  bool isRanked(PIDPair p) const;
  bool isR1(RID r) const;
  bool isR2(RID r) const;
  bool isRankedRi(PID p, RID r) const;
  bool willAccept(PIDPair p) const;
  bool willAccept(PID p, RID r) const;
  PIDPair matchedTo() const;
  bool isMatched() const;
  void match(PIDPair p) const;
  void unmatch() const;
  RID R1() const;
  RID R2() const;
  const vector<PIDPair>& ROL() const;
};

ostream& operator<<(ostream& os, const CID& c) {
  os << c.id ;
  return os;
}

Problem* RID::prob;
Problem* CID::prob;
Problem* PID::prob;

const PID nilPID {-1};
const PIDPair nilPPID {nilPID, nilPID};
const RID nilRID {-1};
const CID nilCID {-1};

class Problem {
public:
  Problem() : residents {}, programs {}, couples {},
	      errMsg {}, probOK {true}, resIDs {}, progIDs {},
	      cplIDs {}, progsRanked {}, resRanked {}
  {
    RID::prob  = this;
    CID::prob = this;
    PID::prob = this;
  }

  Program& ithProg(PID id);
  Resident& ithRes(RID id);
  Couple& ithCpl(CID id);

  //Problem IO and error processing
  bool readProblem(string filename);
  void readResident(string l);
  void readCouple(string l);
  void readProgram(string l);

  //  Post and Error processing
  void postProcess();
  bool chkID(int rid, unordered_set<int>& Ids, string errmsg);
  void furtherInputChecks();
  void clearErrVecs();
  void postError(string msg) {
    errMsg += msg;
    probOK = false;
  }
  bool ok() { return probOK; }
  string& getError() { return errMsg; }
  friend ostream& operator<<(ostream& os, const Problem& prob);

  void printMatchStats();

  const vector<Resident>& Res() const { return residents; }
  const vector<Program>& Prog() const { return programs; }
  const vector<Couple>& Cpl() const { return couples; }

private:
  vector<Resident> residents;
  vector<Program> programs;
  vector<Couple> couples;
  string errMsg;
  bool probOK;
  unordered_set<int> resIDs;
  unordered_set<int> progIDs;
  unordered_set<int> cplIDs;
  vector<int> progsRanked;
  vector<int> resRanked;
};

//Generic Output specializations
template<typename T>
ostream& operator<<(ostream& os, const vector<T>& v) {
  os << "[ ";
  for(const auto& i : v) 
    os << i << " ";
  os << "] (" << v.size() << ")";
  return os;
}

template<typename T>
ostream& operator<<(ostream& os, const pair<T,T>& p) {
  os << "(" << p.first << ", " << p.second << ")";
  return os;
}

//Classes 
class Resident {
 public:
  RID id;
  Resident() : id {nilRID}, rol{}, c {nilCID}, m {nilPID} {} //Default constructor==nullResident
  Resident(RID ident, vector<PID> rankedPrograms, int couple = nilCID) : 
    id {ident},
    rol {rankedPrograms},
    c {couple},
    m {nilPID}
  { }

  operator RID() const { return id; } 

  int rankOf(PID p) const {
    if (p == nilPID) 
      return rol.size();
    auto it = std::find(rol.begin(), rol.end(), p);
    if(it == rol.end())
      return std::numeric_limits<int>::max();      
    else
      return std::distance(rol.begin(), it);
  }

  bool prefers(PID p1, PID p2) const {
    return rankOf(p1) < rankOf(p2);
  }

  bool isRanked(PID p) const {
    return rankOf(p) <= static_cast<int>(rol.size());
  }

  bool willAccept(PID p) const {
    //Assumes resident not currently matched to p
    if(id == nilRID)
      return true;
    return rankOf(p) < rankOf(matchedTo());
  }

  PID matchedTo() const { return m; }
  bool isMatched() const { return m != nilPID; }

  void match(PID prog) { //does not check ranking
    m = prog;
  }

  void unmatch() { match(nilPID); }
    
  bool inCouple() const { return c != nilCID; }
  CID couple() const { return c; }
  RID partner() const {
    if(!inCouple())
      return nilRID;
    if(couple().R1() == id)
      return couple().R2();
    else
      return couple().R1();
  }

  const vector<PID>& ROL() const { return rol; }

  friend void Problem::postProcess();

 private:
  vector<PID> rol;
  CID c;
  PID m;
};

inline ostream& operator<<(ostream& os, const Resident& r) {
  os << "Resident " << r.id << ". ";
  os << " match = " << r.matchedTo() << " ";
  if(r.inCouple())
    os << "in couple " << r.couple() << "\n";
  else
    os << "Not in couple (" << r.couple() << ")\n";
  os << "ROL = " << r.ROL() << "\n";
  return os;
}

class Couple {
 public:
  CID id;
  Couple() : id {nilCID}, rol {}, r1 {nilRID}, r2 {nilRID} {} //default constructor==nullCouple
  Couple(CID ident, RID res1, RID res2, vector<PIDPair> rankedPrograms) :
    id {ident},
    rol {rankedPrograms},
    r1 {res1},
    r2 {res2}
  {}

  operator CID() const { return id; } 

  int rankOf(PIDPair p) const {
    if(p == nilPPID)
      return rol.size();
    auto it = std::find(rol.begin(), rol.end(), p);
    if(it == rol.end())
      return std::numeric_limits<int>::max();      
    else
      return std::distance(rol.begin(), it);
  }

  bool prefers(PIDPair p1, PIDPair p2) const  { return rankOf(p1) < rankOf(p2); }
  bool isRanked(PIDPair p) const { return rankOf(p) <= static_cast<int>(rol.size()); }
  bool isR1(RID r) const { return r == r1; }
  bool isR2(RID r) const { return r == r2; }

  bool isRankedRi(PID p, RID r) const { //ranked by r[1/2]
    if(p == nilPID) 
      return true;
    if(id == nilCID)
      return true;

    if(r == r1) {
      auto ranksP = [p](PIDPair x) {return x.first == p;};
      auto it = std::find_if(rol.begin(), rol.end(), ranksP);
      return it != rol.end();
    }
    else {
      auto ranksP = [p](PIDPair x) {return x.second == p;};
      auto it = std::find_if(rol.begin(), rol.end(), ranksP);
      return it != rol.end();
    }
  }

  bool willAccept(PIDPair p) const {
    //In: couple not currently matched to p
    if(id == nilCID)
      return true;
    return rankOf(p) < rankOf(matchedTo());
  }

  bool willAccept(PID p, RID r) const {
    //r (either r1 or r2) finds some program pair where
    //r is matched to p, superior to the couple's current match
    if(r == r1)
      return willAcceptR1(p);
    else
      return willAcceptR2(p);
  }

  bool willAcceptR1(PID p) const {
    //there is a better available match for the couple with r1 going into p.
    auto lim = rankOf(matchedTo());
    for(size_t i = 0 ; i < rol.size() && i < static_cast<size_t>(lim); i++) {
      if(rol[i].first != p)
	continue;
      if(rol[i].second.willAccept(r2))
	return true;
    }
    return false;
  }

  bool willAcceptR2(PID p) const {
    //there is a better available match for the couple with r2 going into p.
    auto lim = rankOf(matchedTo());
    for(size_t i = 0 ; i < rol.size() && i < static_cast<size_t>(lim); i++) {
      if(rol[i].second != p)
	continue;
      if(rol[i].first.willAccept(r1))
	return true;
    }
    return false;
  }

  PIDPair matchedTo() const { return std::make_pair(r1.matchedTo(), r2.matchedTo()); }
  bool isMatched() const { return r1.isMatched() || r2.isMatched(); }

  void match(PIDPair p) { //does not check ranking
    r1.match(p.first);
    r2.match(p.second);
  }

  void unmatch() { match({nilPID, nilPID}); }

  RID R1() const { return r1; }
  RID R2() const { return r2; }
  const vector<PIDPair>& ROL() const { return rol; }

  friend void Problem::postProcess();
 
private:
 vector<PIDPair> rol;
 RID r1;
 RID r2;
};

inline ostream& operator<<(ostream& os, const Couple& c) {
  os << "Couple " << c.id << ". ";
  os << "r1 = " << c.R1() << " r2 = " << c.R2();
  os << " match = " << c.matchedTo() << " ";
  os << "ROL = " << c.ROL() << "\n";
  return os;
}

class Program {
public:
  PID id;
  Program() : id {nilPID}, q {std::numeric_limits<int>::max()},
	      rol {}, accepted {} {} //default constructor==nullProgram
  Program(PID ident, int quota, vector<RID> rankedResidents) :
    id {ident},
    q {quota},
    rol {rankedResidents},
    accepted {}
  {}

  operator PID() const { return id; } 

  RID minRes() const { return (nmatched() > q-1) ? accepted[q-1] : nilRID; }
  RID min2ndRes() const { return (nmatched() > q-2) ? accepted[q-2] : nilRID; }

  int rankOf(RID r) const {
    if(r == nilRID) 
      return rol.size();

    auto it = std::find(rol.begin(), rol.end(), r);
    if(it == rol.end())
      return std::numeric_limits<int>::max();      
    else
      return std::distance(rol.begin(), it);
  }

  bool prefers(RID r1, RID r2) const { return rankOf(r1) < rankOf(r2); }
  bool isRanked(RID r) const { return rankOf(r) <= static_cast<int>(rol.size()); }

  bool willAccept(RID r) const {
    //In: r is not currently accepted in program
    if(id == nilPID)
      return true;
    if(QUOTA() <= 0)
      return false;
    return rankOf(r) < rankOf(minRes());
  }

  bool willAccept(RID r1, RID r2) const {
    //In: neither r1 nor r2 is currently accepted in program
    if(id == nilPID)
      return true;
    if(QUOTA() <= 1)
      return false;
    return
      rankOf(r1) < rankOf(min2ndRes()) && rankOf(r2) < rankOf(min2ndRes());
  }
  
  int nmatched() const { return accepted.size(); }

  vector<RID> match(RID r) {
    //does not check ranking
    vector<RID> bumped {};
    if(r == nilRID) {
      cout << "Processing Error: Tried to match nil Resident into Program\n";
      return bumped;
    }

    if(nmatched() == q) {
      bumped.push_back(accepted.back());
      accepted.pop_back();
    }
    accepted.push_back(r);
    sort_accept();
    return bumped;
  }
	
  vector<RID> match(RID r1, RID r2) {
    vector<RID> bumped {};
    if(r1 == nilRID || r2 == nilRID) {
      cout << "Processing Error: Tried to match pair with nil Resident into Program\n";
      return bumped;
    }

    while(nmatched() >= q-1) {
      bumped.push_back(accepted.back());
      accepted.pop_back();
    }
    accepted.push_back(r1);
    accepted.push_back(r2);
    sort_accept();
    
    return bumped;
  }

  void unmatch(RID r) {
    auto it = std::find(accepted.begin(), accepted.end(), r);
    if(it != accepted.end())
      accepted.erase(it);
  }

  int QUOTA() const { return q; }
  const vector<RID>& ACCEPTED() const { return accepted; }
  const vector<RID>& ROL() const { return rol; }

  friend void Problem::postProcess();

private:
  int q;
  vector<RID> rol;
  vector<RID> accepted;
  void sort_accept() {
    auto ranking = [this](RID r1, RID r2){ return prefers(r1, r2); };
    std::sort(accepted.begin(), accepted.end(), ranking);
  }
};

inline ostream& operator<<(ostream& os, const Program& p) {
  os << "Program " << p.id << ". ";
  os << "quota = " << p.QUOTA() << "\n";
  os << "accepted  = " << p.ACCEPTED() << "\n";
  os << "ROL = " << p.ROL() << "\n\n";
  return os;
}

Resident nullResident {};
Couple nullCouple {};
Program nullProgram {}; 

//Access to objects via IDs
Program& Problem::ithProg(PID id) {
  if(id == nilPID) {
    //cout << "Processing Error: Tried to find object for nil Program\n";
    return nullProgram;
  }
  else
    return programs[id];
}

Resident& Problem::ithRes(RID id) {
  if(id == nilRID) {
    //cout << "Processing Error: Tried to find object for nil Resident\n";
    return nullResident;
  }
  else
    return residents[id];
}

Couple& Problem::ithCpl(CID id) {
  if(id == nilCID) {
    cout << "Processing Error: Tried to find object for nil Couple\n";
    return nullCouple;
  }
  else
    return couples[id];
}

//Direct call of object functionality via IDs
int RID::rankOf(PID p) const { return (prob->ithRes(id)).rankOf(p); }
bool RID::prefers(PID p1, PID p2) const { return (prob->ithRes(id)).prefers(p1, p2); }
bool RID::isRanked(PID p) const { return (prob->ithRes(id)).isRanked(p); }
bool RID::willAccept(PID p) const { return (prob->ithRes(id)).willAccept(p); }
PID RID::matchedTo() const { return (prob->ithRes(id)).matchedTo(); }
bool RID::isMatched() const{ return (prob->ithRes(id)).isMatched(); }
void RID::match(PID prog) const { (prob->ithRes(id)).match(prog); }
void RID::unmatch() const { (prob->ithRes(id)).unmatch(); }
bool RID::inCouple() const { return (prob->ithRes(id)).inCouple(); }
CID RID::couple() const { return (prob->ithRes(id)).couple(); }
RID RID::partner() const { return (prob->ithRes(id)).partner(); }
const vector<PID>& RID::ROL() const { return (prob->ithRes(id)).ROL(); }

int CID::rankOf(PIDPair p) const { return (prob->ithCpl(id)).rankOf(p); }
bool CID::prefers(PIDPair p1, PIDPair p2) const { return (prob->ithCpl(id)).prefers(p1, p2); }
bool CID::isRanked(PIDPair p) const { return (prob->ithCpl(id)).isRanked(p); }
bool CID::isR1(RID r) const { return (prob->ithCpl(id)).isR1(r); }
bool CID::isR2(RID r) const { return (prob->ithCpl(id)).isR2(r); }
bool CID::isRankedRi(PID p, RID r) const { return (prob->ithCpl(id)).isRankedRi(p, r); }
bool CID::willAccept(PIDPair p) const { return (prob->ithCpl(id)).willAccept(p); }
bool CID::willAccept(PID p, RID r) const { return (prob->ithCpl(id)).willAccept(p,r); }
PIDPair CID::matchedTo() const { return (prob->ithCpl(id)).matchedTo(); }
bool CID::isMatched() const { return (prob->ithCpl(id)).isMatched(); }
void CID::match(PIDPair p) const { (prob->ithCpl(id)).match(p); }
void CID::unmatch() const { (prob->ithCpl(id)).unmatch(); }
RID CID::R1() const { return (prob->ithCpl(id)).R1(); }
RID CID::R2() const { return (prob->ithCpl(id)).R2(); }
const vector<PIDPair>& CID::ROL() const { return (prob->ithCpl(id)).ROL(); }

RID PID::minRes() const { return (prob->ithProg(id)).minRes(); }
RID PID::min2ndRes() const { return (prob->ithProg(id)).min2ndRes(); }
int PID::rankOf(RID r) const { return (prob->ithProg(id)).rankOf(r); }
bool PID::prefers(RID r1, RID r2) const { return (prob->ithProg(id)).prefers(r1, r2); }
bool PID::isRanked(RID r) const { return (prob->ithProg(id)).isRanked(r); }
bool PID::willAccept(RID r) const { return (prob->ithProg(id)).willAccept(r); }
bool PID::willAccept(RID r1, RID r2) const { return (prob->ithProg(id)).willAccept(r1, r2); }
int PID::nmatched() const { return (prob->ithProg(id)).nmatched(); }
vector<RID> PID::match(RID r) const { return (prob->ithProg(id)).match(r); }
vector<RID> PID::match(RID r1, RID r2) const { return (prob->ithProg(id)).match(r1, r2); }
void PID::unmatch(RID r) const { (prob->ithProg(id)).unmatch(r); }
int PID::QUOTA() const { return (prob->ithProg(id)).QUOTA(); }
const vector<RID>& PID::ACCEPTED() const { return (prob->ithProg(id)).ACCEPTED(); }
const vector<RID>& PID::ROL() const { return (prob->ithProg(id)).ROL(); }


bool Problem::readProblem(string filename) {
  std::ifstream in {filename};
  vector<string> ilines;
  string line;
  while(getline(in, line))
    ilines.push_back(line);
  for(auto l : ilines) {
    if(l.size() == 0)
      continue;
    switch( l[0] ) {
    case ' ':
      break;
    case '#':
      break;
    case 'r':
      readResident(l);
      break;
    case 'c':
      readCouple(l);
      break;
    case 'p':
      readProgram(l);
      break;
    default:
      postError("Input ERROR: line \"" + l + "\" from input is invalid\n");
    }
  }
  furtherInputChecks();
  clearErrVecs();
  postProcess();
  return ok();
}

bool Problem::chkID(int rid, unordered_set<int>& Ids, string errmsg) {
  auto fnd = Ids.find(rid);
  if(fnd != Ids.end()) {
    postError(errmsg);
    return false;
  }
  else {
    Ids.insert(rid);
    return true;
  }
}

void Problem::readResident(string l) {
  //Format:
  //"r <resident id==int> <rol>"
  //Where rol is a sequence of program ids most prefered first.
  istringstream iss {l};
  char c;
  int rid, pid;
  vector<int> pids;

  iss >> c >> rid;
  while(iss >> pid) {
    pids.push_back(pid);
    progsRanked.push_back(pid);
  }

  if(rid < 0) {
    postError("Input ERROR: negative Resident ID in resident spec.\n");
    return;
  }
  if(!chkID(rid, resIDs, "Input ERROR: Duplicate resident ID in resident specs.\n"))
    return;

  if(static_cast<int>(residents.size()) <= rid)
    residents.resize(rid+1);

  vector<PID> _pids;
  for(auto p : pids) 
    _pids.push_back(p); //auto type conversion int -->xIDs
  residents[rid] = Resident(rid, _pids);
}
    
void Problem::readCouple(string l) {
  //Format:
  //"c <couple id> <r1id> <r2id> <rol>"
  //The couple id, followed by the two resident ids.
  //Neither resident can have appeared before.
  //rol is an even number of program ids. They are regarded 
  //as pairs with the most preferred pair comming as the first
  //two program ids. 
  //Note -1 is a legit progam id, denoting the null program. 
  //(e.g., the pair 3 -1 indicates a preference for res1 matching
  //to program 3 and res2 having a null match. 
  istringstream iss {l};
  char c;
  int r1id, r2id, cid, pid;
  vector<int> pids;

  iss >> c >> cid >> r1id >> r2id;
  while(iss >> pid) {
    pids.push_back(pid);
    progsRanked.push_back(pid);
  }

  if(pids.size() % 2 != 0) {
    postError("Input ERROR: Couple input had odd number or programs specified (not pairs)\n");
    return;
  }

  if(!chkID(r1id, resIDs, "Input ERROR: Duplicate resident ID in couple spec.\n"))
    return;
  if(r1id != r2id &&
     !chkID(r2id, resIDs, "Input ERROR: Duplicate resident ID in couple spec.\n"))
    return;
  if(!chkID(cid, cplIDs, "Input ERROR: Duplicate couple ID in couple specs.\n"))
    return;
  if(r1id < 0 || r2id < 0) {
    postError("Input ERROR: negative resident ID in couple spec\n");
    return;
  }
  
  if(static_cast<int>(couples.size()) <= cid)
    couples.resize(cid+1);
  vector<PIDPair> ppairs {};
  for(size_t i = 0; i < pids.size(); i += 2) 
    ppairs.push_back({pids[i], pids[i+1]});
  couples[cid] = Couple(cid, r1id, r2id, ppairs);

  if(static_cast<int>(residents.size()) <= r1id)
    residents.resize(r1id+1);
  residents[r1id] = Resident(r1id, {}, cid);
  if(static_cast<int>(residents.size()) <= r2id)
    residents.resize(r2id+1);
  residents[r2id] = Resident(r2id, {}, cid);
}

void Problem::readProgram(string l) {
  //Format
  //"p <program id> <quota> <rol>"
  istringstream iss {l};
  char c;
  int pid, rid, quota;
  vector<int> rids;

  iss >> c >> pid >> quota;
  while(iss >> rid) {
    rids.push_back(rid);
    resRanked.push_back(rid);
  }

  if(!chkID(pid, progIDs, "Input ERROR: Duplicate program ID in program specs.\n"))
    return;

  if(static_cast<int>(programs.size()) <= pid)
    programs.resize(pid+1);
  
  vector<RID> _rids;
  for(auto r : rids) 
    _rids.push_back(r);

  programs[pid] = Program(pid, quota, _rids);
}

void Problem::furtherInputChecks() {
  for(auto pid : progsRanked) {
    if(pid != -1) {
      auto fnd = progIDs.find(pid);
      if(fnd == progIDs.end()) 
	postError("Input ERROR: Resident or Couple ranked unspecified program.\n");
    }
  }
  for(auto rid : resRanked) {
    auto fnd = resIDs.find(rid);
    if(fnd == resIDs.end()) 
      postError("Input ERROR: Program unspecified resident.\n");
  }
}

void Problem::clearErrVecs() {
  resIDs = unordered_set<int> {};
  progIDs = unordered_set<int> {};
  cplIDs = unordered_set<int> {};
  progsRanked = vector<int> {};
  resRanked = vector<int> {};
}

void Problem::postProcess() {
  //remove rankings that are unreciprocated
  //friend of all classes so can access rol vectors.
  for(auto& r : residents) {
    size_t j {0};
    for(auto p : r.rol) {
      if(p.isRanked(r)) 
	r.rol[j++] = p; //p ranks r
    }
    r.rol.resize(j);
    //    r.rol.push_back(nilPID); //nullProgram is least preferred but acceptable
  }
  for(auto& c : couples) {
    size_t j {0};
    for(auto p : c.rol)
      if((p.first == nilPID || (p.first).isRanked(c.r1)) 
	 && (p.second == nilPID || (p.second).isRanked(c.r2)))
	c.rol[j++] = p;
    c.rol.resize(j);
    //    c.rol.push_back(nilPPID);
  }
  for(auto& p : programs) {
    size_t j {0};
    for(auto r : p.rol) {
      if(r.inCouple()) {
	if(r.couple().isRankedRi(p, r))
	  p.rol[j++] = r;
      }
      else {
	if(r.isRanked(p))
	  p.rol[j++] = r;
      }
    }
    p.rol.resize(j);
    //    p.rol.push_back(nilRID);
  }
}

void Problem::printMatchStats() {
  int resNotMatched {0};
  int cplNotMatched {0};
  int progSpareCap {0};
  int nSingRes {0};
  int resGotTopRank {0};
  int cplGotTopRank {0};
  int prgGotTopRank {0};
  
  double resAveRank {0};
  double cplAveRank {0};
  double prgAveRank {0};
  
  
  for(const auto&r : residents) 
    if(!r.inCouple()) {
      ++nSingRes;

      if(!r.isMatched()) 
	++resNotMatched;
      else
	resAveRank += r.rankOf(r.matchedTo());
      if(r.rankOf(r.matchedTo()) == 0)
	++resGotTopRank;
    }

  for(const auto&c : couples) {
    if(!c.isMatched())
      ++cplNotMatched;
    else
      cplAveRank += c.rankOf(c.matchedTo());      
    if(c.rankOf(c.matchedTo()) == 0)
      ++cplGotTopRank;
  }

  int matchedProgs {0};
  for(const auto&p : programs) {
    progSpareCap += p.QUOTA() - p.ACCEPTED().size();
    double aveRank {0};
    for(const auto &res : p.ACCEPTED()) {
      aveRank += p.rankOf(res);
      if(p.rankOf(res) == 0)
	++prgGotTopRank;
    }
    if(p.ACCEPTED().size() > 0) {
      prgAveRank += aveRank/p.ACCEPTED().size();
      ++matchedProgs;
    }
  }

  cout << "#Matching Summary Stats:\n";
  cout << "#Unmatched Singles: " << resNotMatched << "\n";
  cout << "#Unmatched Couples: " << cplNotMatched << "\n";
  cout << "#Unmatched Program slots: " << progSpareCap << "\n";

  if(nSingRes-resNotMatched > 0)
    cout << "#Ave Resident Rank of their matching = "
	 << resAveRank/(nSingRes-resNotMatched) << "\n";
  cout << "#Num Residents getting their top rank = "
       << resGotTopRank << "\n";

  if(couples.size() - cplNotMatched > 0)
    cout << "#Ave Couple Rank of their matching = "
	 << cplAveRank/(couples.size()-cplNotMatched) << "\n";
  cout << "#Num Couples getting their top rank = "
       << cplGotTopRank << "\n";
    
  if(matchedProgs > 0) 
    cout << "#Ave Program Rank of their matched residents "
	 << prgAveRank/matchedProgs << "\n";
  cout << "#Num Programs getting their top rank = "
       << prgGotTopRank;
  cout << "\n";
}

inline ostream& operator<<(ostream& os, const Problem& prob) {
  os << "Problem Spec\nResidents:\n";
  for(auto& res : prob.residents) 
    os << res;
  os << "\nCouples:\n";
  for(auto& cpl : prob.couples)
    os << cpl;
  os << "\nPrograms:\n";
  for(auto& prog: prob.programs)
    os << prog;
  return os;
}

class MatchChk {
public:
  MatchChk(Problem* p) : prob {p}, errMsg {}, checkOK {true}, nomatch {true} {}

  //Problem IO and error processing
  bool readMatch(string filename);
  void readResident(string l);
  void readValid(string l);

  //  Post and Error processing
  bool check();
  void checkSingle(RID r);
  void checkCouple(CID c);
  void checkCoupleResident(RID r);

  void postError(string msg) {
    errMsg += msg;
    checkOK = false;
  }
  bool ok() { return checkOK; }
  bool noMatch() { return nomatch; }
       
  string& getError() { return errMsg; }

  friend ostream& operator<<(ostream& os, const MatchChk& match);

private:
  Problem* prob;
  string errMsg;
  bool checkOK;
  bool nomatch;
};

bool MatchChk::readMatch(string filename) {
  std::ifstream in {filename};
  vector<string> ilines;
  string line;
  while(getline(in, line))
    ilines.push_back(line);
  for(auto l : ilines) {
    if(l.size() == 0)
      continue;
    switch( l[0] ) {
    case ' ':
      break;
    case '#':
      break;
    case 'r':
      readResident(l);
      break;
    case 'm':
      readValid(l);
      break;
    default:
      postError("Input ERROR: line \"" + l + "\" from input is invalid\n");
    }
  }
  return ok();
}

void MatchChk::readResident(string l) {
  //Format:
  //"r <rid> <pid>"
  //Where resident "rid" is matched to program "pid"
  istringstream iss {l};
  char c;
  int r, p;

  iss >> c >> r >> p;

  if(r < 0) {
    postError("Input ERROR: negative ID in resident spec.\n");
    return;
  }

  RID rid (r);
  PID pid (p);
  rid.match(p);
  if(pid != nilPID)
    pid.match(r);
}

void MatchChk::readValid(string l) {
  //Format:
  //"m [0/1]"
  //0 indicates that no match was found. 1 a match that has to be checked.
  istringstream iss {l};
  char c;
  int m;
  iss >> c >> m;
  if(m == 1)
    nomatch = false;
  else
    nomatch = true;
}

bool MatchChk::check() {
  if(nomatch)
    return true;
  for(auto& res : prob->Res()) {
    if(!res.inCouple()) {
      checkSingle(res);
    }
    else {
      checkCouple(res.couple());
    }
  }
  return checkOK;
}

void MatchChk::checkSingle(RID res) {
  auto pid = res.matchedTo();
  if(pid != nilPID) {
    if(!res.isRanked(pid) || !pid.isRanked(res)) {
      ostringstream oss {};
      oss << "ERROR: Resident " << res.id << "= " << pid 
	  << ". Don't rank each other\n";
      postError(oss.str());
    }
    auto it = std::find(pid.ACCEPTED().begin(), pid.ACCEPTED().end(), res.id);
    if(it == pid.ACCEPTED().end()) {
      ostringstream oss {};
      oss << "ERROR: Resident " << res.id << "= " << pid 
	  << ". Program did not accept\n";
      postError(oss.str());
    }
  }
  for(auto pid0: res.ROL()) {
    if(pid0 == pid)
      break;
    if(pid0.willAccept(res)) {
      ostringstream oss {};
      oss << "ERROR: Resident " << res.id << "= " << pid 
	  << ". Resident would match to higher ranked program "
	  << pid0 << "\n";
      postError(oss.str());
    }
  }
}

void MatchChk::checkCouple(CID c) {
  auto ppid = c.matchedTo();
  if(ppid == nilPPID)
    return;
  if(!c.isRanked(ppid)) {
    ostringstream oss {};
    oss << "ERROR: Couple " << c.id << "= " << ppid 
	<< ". 'doesn't rank program pair\n";
    postError(oss.str());
  }
  
  auto pid1 = ppid.first;
  auto pid2 = ppid.second;
  if(pid1==nilPID || pid2 == nilPID)
    checkCoupleResident(pid1 == nilRID ? c.R2() : c.R1());
  else {
    checkCoupleResident(c.R1());
    checkCoupleResident(c.R2());
  }

  //now check for better feasible match
  for(auto ppid0: c.ROL()) {
    if(ppid0 == ppid)
      break;
    if((ppid0.first == ppid0.second &&  ppid0.first.willAccept(c.R1(), c.R2()))
       || (ppid0.first != ppid0.second 
	   && (ppid0.first == nilPID || ppid0.first.willAccept(c.R1()))
	   && (ppid0.second == nilPID || ppid0.second.willAccept(c.R2()))) ) {
      ostringstream oss {};
      oss << "ERROR: Couple " << c.id << "= " << ppid 
	  << ". Resident would match to higher ranked program "
	  << ppid0 << "\n";
      postError(oss.str());
    }
  }
}

void MatchChk::checkCoupleResident(RID rid) {
  auto pid = rid.matchedTo();
  if(!pid.isRanked(rid)) {
    ostringstream oss {};
    oss << "ERROR: Couple " << rid.couple() << "= " << rid.couple().matchedTo()
	<< ". Program does not rank\n";
    postError(oss.str());
  }
  if(pid != nilPID) {
    auto it = std::find(pid.ACCEPTED().begin(), pid.ACCEPTED().end(), rid);
    if(it == pid.ACCEPTED().end()) {
      ostringstream oss {};
      oss << "ERROR: Couple " << rid.couple() << "= " << rid.couple().matchedTo()
	  << ". Program did not accept\n";
      postError(oss.str());
    }
  }
}

inline ostream& operator<<(ostream& os, const MatchChk& match) {
  os << "Match Spec:\n";
  for(auto& r : match.prob->Res()) {
    os << "Resident " << r.id << ". ";
    os << " match = " << r.matchedTo() << " ";
    if(r.inCouple())
      os << "in couple " << r.couple() << "\n";
    else
      os << "Not in couple (" << r.couple() << ")\n";
  }
  return os;
}

/******************************************************************/
int verbosity {};

//TODO change verbosity into a command line option.


int main(int argc, char** argv) {
  setUsageHelp("usage: %s [options] <matching_problem_spec_file> <match_spec_file>\n");
  IntOption verb("MAIN", "verb", "Verbosity level (0=silent, 1=some, 2=more).", 0, IntRange(0,2));
  parseOptions(argc, argv, true);
  if(argc != 3)
    printUsageAndExit(argc, argv);
  verbosity = verb;
  
  Problem prob{};
  MatchChk matchChk {&prob};    

  if(!prob.readProblem(argv[1])) {
    cout << "Problems reading problem file: \"" << argv[1] << "\"\n";
    cout << prob.getError();
    return 1;
  }
  if(!matchChk.readMatch(argv[2])) {
    cout << "Problems reading match file: \"" << argv[2] << "\"\n";
    cout << matchChk.getError();
    return 1;
  }
    
  if(verbosity > 0) {
    cout << "Inputed problem:\n";
    cout << prob;
    cout << "Match:\n";
    cout << matchChk;
  }

  if(matchChk.noMatch()) 
    cout << "No match found.\n";
  else if(!matchChk.check()) {
    cout << "ERROR: Unstable Match.\n";
    cout << matchChk.getError();
    return 1;
  }
  else {
    cout << "Match ok.\n";
    prob.printMatchStats();
  }
  return 0;
}
