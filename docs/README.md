# Sphinx DOC

Hints and notes on how to work with Sphinx.

## pandoc	

pandoc - a super-tool to convert between formats. Sample for markdown conversion:

	sudo apt-get install pandoc
	pandoc --from=markdown --to=rst --output=README.rst README.md


## autodoc

Use sphinxcontrib.pecanwsme.rest and wsmeext.sphinxext plugins to generate API docs

	TODO: why REST URL is not generated with parameters?
  TODO: now that we use jsexpose how will it work? 

## Running sphinx-audobuild

[auto-loader](https://pypi.python.org/pypi/sphinx-autobuild/0.2.3) - rules for convenient doc writing - rebuilds the docs on changes and serves them up. Run and go to http://localhost:8000 

  pip install sphinx-autobuild
	sphinx-autobuild docs/source docs/build/html