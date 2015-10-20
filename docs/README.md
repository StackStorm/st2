# Writing the Docs

## Build and Run the Docs.
The docs are build with Sphinx. It's integrated with the main project Makefile.
`make livedocs` builds the docs and runs the doc site live at [http://localhost:8000](http://localhost:8000)

## Sphinx Tricks

* If the whole section belongs Enterprise Edition, put the following note:
    ```
    .. note::

       Role Based Access Control (RBAC) is only available in StackStorm Enterprise Edition. For
       information about enterprise edition and differences between community and enterprise edition,
       please see `stackstorm.com/product <https://stackstorm.com/product/#enterprise>`_.
    ```
    Refer to Enterprise edition in passing with

        `see Enterprise Edition <https://stackstorm.com/product/#enterprise>`_

* TODO (Use [http://localhost:8000/todo.html](http://localhost:8000/todo.html) for full TODO list (must be empty when we ship)
:

    .. todo:: Here is a TODO

* Code fragment:

    .. code-block: bash

      # List all available triggers
        st2 trigger list

* Reference the document

    :doc:`/start`
    :doc:`in the Rules doc </rules>`

* Referencing an arbitrary section: for instance, there's examples section in sensors.rst. Define a reference on `examples` section in sensors.rst:

         .. _sensors-examples:

    and point to it as from this, or from other documensts as:

           :ref:`sensors-examples`
           :ref:`My examples <sensors-examples>`

    Note that the leading `_` underscore is gone, and the reference is quoted.

    Name convention for references is `_filename-refname` (because they are unique across the docs).  Note that there is no way to reference just a point in the docs. See http://sphinx-doc.org/markup/inline.html#cross-referencing-syntax

* External links:

    `External link <http://webchat.freenode.net/?channels=stackstorm>`_

* Inlcude a document, full body:

    .. include:: /engage.rst

* Link to GitHub st2 repo

    :github_st2:`st2/st2common/st2common/operators.py </st2common/st2common/operators.py>`

* Link  to Github st2contrib repo:

    :github_contrib:`Link to docker README on st2contrib<packs/docker/README.md>`

* Link to st2contrib and st2incubator repos on Github (using a global we set up in source/conf.py)

    `st2contrib`_
    `st2incubator`_

* The pattern to include an example from `/contrib/examples`: make example file name a reference on github. may say that it is deployed to `/usr/share/doc/st2/examples/`, and auto-include the file:

    Sample rule: :github_st2:`sample-rule-with-webhook.yaml
    </contrib/examples/rules/sample-rule-with-webhook.yaml>` :

    .. literalinclude:: /../../contrib/examples/rules/sample_rule_with_webhook.yaml
        :language: json


## Pandoc - convert md <-> rst and more

pandoc - a super-tool to convert between formats. Sample for markdown conversion:

  sudo apt-get install pandoc
  pandoc --from=markdown --to=rst --output=README.rst README.md

## Running docs only

To make docs changes, without installing full development environment (e.g., on Mac or Windows:

```
git clone git@github.com:StackStorm/st2.git
cd st2/docs
virtualenv .venv
. .venv/bin/activate
pip install sphinx sphinx-autobuild
sphinx-autobuild -H 0.0.0.0 -b html ./source/ ./build/html

```

Edit, enjoy live updates.

## Misc

It's ironic that I use Markdown to write about rST tricks.



