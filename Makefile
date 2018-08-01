# Makefile for the Speech to Text System.

CC = clang++
CFLAGS = -Wall -Wextra -std=c++11 -O2

all: STT clean

STT: driver.cpp
		$(CC) -o STT driver.cpp

clean:
			rm -f *.o core *~ driver.o