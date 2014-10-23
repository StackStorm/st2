# Sphinx DOC

Hints and notes on how to work with Sphinx.

Install sphinx, build the docs. 

	pip install sphinx
	sphinx-build -b html docs/source docs/build/html

## pandoc	

pandoc - a super-tool to convert between formats. Sample for markdown conversion:

	sudo apt-get install pandoc
	pandoc --from=markdown --to=rst --output=README.rst README.md


## autodoc and sphinx

Use sphinxcontrib.pecanwsme.rest and wsmeext.sphinxext plugins to generate API docs. But once we replaced WSME with jsexpose, pecanwsme is not working (some hacks needed).
	

## Running sphinx-audobuild

[auto-loader](https://pypi.python.org/pypi/sphinx-autobuild/0.2.3) - rules for convenient doc writing - rebuilds the docs on changes and serves them up. Run and go to http://localhost:8000 

  	pip install sphinx-autobuild
	sphinx-autobuild docs/source docs/build/html

DZ: I added sphinx-autobuild to main st2 Makefile, use  `make autodocs`.

## Cheatsheet

Use [source/cheatsheet.rst](./source/cheatsheet.rst) for: 

1. Compiled TODO from all the docs site (full docs rebuild recommended)
1. .rst samples


