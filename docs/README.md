# Sphinx DOC

Hints and notes on how to work with Sphinx.

## pandoc	

pandoc - a super-tool to convert between formats. Sample for markdown conversion:

	sudo apt-get install pandoc
	pandoc --from=markdown --to=rst --output=README.rst README.md


## autodoc

Use sphinxcontrib.pecanwsme.rest and wsmeext.sphinxext plugins

	TODO: why REST URL is not generated with parameters?

## Running sphinx-audobuild

[auto-loader](https://pypi.python.org/pypi/sphinx-autobuild/0.2.3) - rules for convenient doc writing. See https://pypi.python.org/pypi/sphinx-autobuild/0.2.3. install, and run: 

	sphinx-autobuild docs/source docs/build