# Makefile for NRMO/Loom C++ core
#
# usage:
#   make           # build example_store
#   make run       # build and run
#   make clean

CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall

TARGET = example_store
SRC    = example_store.cpp
HDR    = nrmo_core.hpp

all: $(TARGET)

$(TARGET): $(SRC) $(HDR)
	$(CXX) $(CXXFLAGS) $(SRC) -o $(TARGET)

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET)

.PHONY: all run clean
