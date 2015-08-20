MSRCS = System.cc Options.cc params.cc problem.cc rcp.cc rpmatcher.cc match_main.cc kprmatcher.cc
MHRDS = io.h params.h problem.h rcp.h rpmatcher.h damatcher.h kprmatcher.h
VSRCS = verifier.cc Options.cc
MOBJS = $(MSRCS:.cc=.o)
VOBJS = $(VSRCS:.cc=.o)

ECHO=@echo
MATCHRP = matchrp
VERIFIER = matchvf

MATCH_CXXFLAGS = -std=c++0x -Wall
MATCH_CXXFLAGS += -D __STDC_LIMIT_MACROS -D __STDC_FORMAT_MACROS 
MATCH_CXXFLAGS += -I .

MATCH_LDFLAGS = -Wall --static

a:  MATCH_CXXFLAGS += -O3 -D NDEBUG
a:  $(MATCHRP) $(VERIFIER) 

da: MATCH_CXXFLAGS += -O0 -U NDEBUG  -ggdb
da: $(MATCHRP) $(VERIFIER) 

dm: MATCH_CXXFLAGS += -O0 -U NDEBUG -ggdb
dm: $(MATCHRP)
m:  MATCH_CXXFLAGS += -O3 -D NDEBUG
m: $(MATCHRP)

v: $(VERIFIER)
dv: addebug $(VERIFIER) 

$(MATCHRP) : $(MOBJS)
$(VERIFIER) : $(VOBJS)

%.o : %.cc $(MHRDS)
	$(ECHO) Compiling: $@
	$(CXX) $(MATCH_CXXFLAGS) $(CXXFLAGS) -c -o $@ $< 

$(MATCHRP):
	$(ECHO) Linking $@
	$(VERB) $(CXX) $^ $(MATCH_LDFLAGS) $(LDFLAGS) -g -o $@

$(VERIFIER):
	$(ECHO) Linking $@
	$(VERB) $(CXX) $^ $(MATCH_LDFLAGS) $(LDFLAGS) -o $@

clean:
	rm -f *.o matchrp matchvf
