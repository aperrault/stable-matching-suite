/***********[rpmatch_main.cc]

-------

Main function for reading in an matching problem and finding a match 
with the Roth Peranson algorith.

------

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
#include <iostream>
#include <errno.h>
#include <signal.h>
#include <limits>
#include "problem.h"
#include "damatcher.h"
#include "rpmatcher.h"
#include "kprmatcher.h"
//#include "minisat/utils/System.h"
#include "minisat/utils/Options.h"
#include "params.h"

using Minisat::setUsageHelp;
using Minisat::printUsageAndExit;
using Minisat::BoolOption;
using Minisat::IntOption;
using Minisat::IntRange;
using Minisat::parseOptions;
using std::cout;
using std::cerr;

static int vnumMajor {1};
static int vnumMinor {5};

static DAmatcher* dam{};

static void SIGINT_exit(int signum) {
    if (dam) {
        cout << "#ERROR: Caught Signal\n";
        dam->printStatsAndExit(signum, 1);
    } else {
        cout.flush();
        cerr.flush();
        _exit(0);
    }
}

int main(int argc, char** argv) {
  try{
    setUsageHelp("usage: %s [options] <matching_problem_spec_file>\n");
    BoolOption version("MAIN", "version", "Print verision number and exit\n", false);
    IntOption cpu_lim("MAIN", "cpu-lim",
		      "Limit on CPU time allowed in seconds (-1 no limit).\n",
		      -1,
		      IntRange(-1, std::numeric_limits<int>::max()));
    IntOption mem_lim("MAIN", "mem-lim",
		      "Limit on memory usage in megabytes (-1 no limit)\n",
		      -1,
		      IntRange(-1, std::numeric_limits<int>::max()));

    parseOptions(argc, argv, true);
    if(version) {
      cout << "matchrp " << vnumMajor << "." << vnumMinor << "\n";
      return(0);
    }
    if (cpu_lim >= 0){
      rlimit rl;
      getrlimit(RLIMIT_CPU, &rl);
      if (rl.rlim_max == RLIM_INFINITY || (rlim_t)cpu_lim < rl.rlim_max){
	rl.rlim_cur = cpu_lim;
	if (setrlimit(RLIMIT_CPU, &rl) == -1)
	  cout <<"# WARNING! Could not set resource limit: CPU-time.\n";
      }
    }
    if (mem_lim >= 0){
      rlim_t new_mem_lim = (rlim_t)mem_lim * 1024*1024;
      rlimit rl;
      getrlimit(RLIMIT_AS, &rl);
      if (rl.rlim_max == RLIM_INFINITY || new_mem_lim < rl.rlim_max){
	rl.rlim_cur = new_mem_lim;
	if (setrlimit(RLIMIT_AS, &rl) == -1)
	  cout << "c WARNING! Could not set resource limit: Virtual memory.\n";
      }
    }
    params.readOptions();
    cout << "#matchrp " << vnumMajor << "." << vnumMinor << "\n";
    if(params.algo == 0)
      if(!params.rnd)
	cout << "#matchrp using Roth Peranson 1999 algorithm with static couple ordering\n";
      else
	cout << "#matchrp using Roth Peranson 1999 algorithm with re-randomization of couple ordering\n";
    else if(params.algo == 2)
      cout << "#matchrp using Kojima Pathak Roth appendix B.2 algorithm\n";

    if(argc != 2) 
      printUsageAndExit(argc, argv);

    signal(SIGINT, SIGINT_exit);
    signal(SIGXCPU, SIGINT_exit);
    signal(SIGSEGV, SIGINT_exit);
    signal(SIGTERM, SIGINT_exit);
    signal(SIGABRT, SIGINT_exit);

    Problem prob {};
    if(!prob.readProblem(argv[1])) {
      cout << "Problems reading input file: \"" << argv[1] << "\"\n";
      cout << prob.getError();
      return 1;
    }
    if(params.verbosity > 0) {
      cout << "#Problem Read:\n";
      if(params.verbosity > 2) 
	cout << prob;
    }

    if(params.algo == 0)
      dam = new RPmatcher {};
    else
      dam = new KPRmatcher {};
    
    auto match = dam->match(prob);
    dam->printStats();
    cout << "#Final Match\n";
    prob.printMatch(match);
  }
  catch(std::bad_alloc) {
    cout << "#ERROR: could not allocate memory\n";
    dam->printStatsAndExit(100, 1);
  }
  catch (...) {
    cout << "#ERROR: unknown exception\n";
    dam->printStatsAndExit(100, 1);
  }
  cout.flush();
  cerr.flush();
  return 0;
}
    
