# Writing the Docs

## Build and Run the Docs. 
The docs are build with Sphinx. It's integrated with the main project Makefile. 
`make livedocs` builds the docs and runs the doc site live at [http://localhost:8000](http://localhost:8000)

## Sphinx Tricks

* TODO (Use [http://localhost:8000/todo.html](http://localhost:8000/todo.html) for full TODO list (must be empty when we ship)
:

		.. todo:: Hers is all TODO 

* Code fragment:

		.. code-block: bash
		
			# List all available triggers
    		st2 trigger list
    			
* Reference the document

		:doc:`/start`

* External links: 

		`External link <http://webchat.freenode.net/?channels=stackstorm>`_ 

Inlcude a document

		.. include:: /engage.rst

* Link to GitHub st2 repo

 		:github_st2:`st2/st2common/st2common/operators.py </st2common/st2common/operators.py>`

* Link  to Github st2contrib repo: 
 
		:github_contrib:`Link to docker README on st2contrib<packs/docker/README.md>`

* Link to st2contrib repo on Github (using a global we set up in source/conf.py)

		`st2contrib`_ or `st2contrib community repo <st2contrib>`_ 

* The pattern to include an example from `/contrib/examples`: make example file name a reference on github. may say that it is deployed to `/usr/share/doc/st2/examples/`, and auto-include the file:

		Sample rule: :github_st2:`sample-rule-with-webhook.json 
		</contrib/examples/rules/sample-rule-with-webhook.json>` : 
		
		.. literalinclude:: /../../contrib/examples/rules/sample_rule_with_webhook.json
    		:language: json
    		
* Referencing an arbitrary section: mark examples as reference: define reference as `.. _sensors-examples` and point to it as :ref:`sensors-examples`. Name convention for references is `_filename-refname` (because they are unique across the docs). Works across the docs, too. Note that there is no way to reference just a point in the docs. See http://sphinx-doc.org/markup/inline.html#cross-referencing-syntax


## Pandoc - convert md <-> rst and more

pandoc - a super-tool to convert between formats. Sample for markdown conversion:

	sudo apt-get install pandoc
	pandoc --from=markdown --to=rst --output=README.rst README.md

## Misc

It's ironic that I use Markdown to write about rST tricks. 



