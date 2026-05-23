.PHONY: install index eval eval-gen doctor start

install:
	./install.sh

index:
	. .venv/bin/activate && cadbury index

eval:
	. .venv/bin/activate && cadbury eval

eval-gen:
	. .venv/bin/activate && cadbury eval --generation

doctor:
	. .venv/bin/activate && cadbury doctor

start:
	. .venv/bin/activate && cadbury start
