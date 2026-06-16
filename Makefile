.PHONY: install index eval eval-gen doctor start

install:
	./install.sh

index:
	. .venv/bin/activate && irona index

eval:
	. .venv/bin/activate && irona eval

eval-gen:
	. .venv/bin/activate && irona eval --generation

doctor:
	. .venv/bin/activate && irona doctor

start:
	. .venv/bin/activate && irona start
