Contrib
=======
1. St2 contents that will be shipped with the product.  These contents will be copied over to /opt/stackstorm on install and then auto-registered.  Users are expected to be able to edit these contents post install:

	* `st2/contrib/core`
	* `st2/contrib/packs`
	* `st2/contrib/linux`
	* `st2/contrib/chatops`

2. St2 samples that may be of interest to the users.  These samples will be shipped with the product but will not be auto-registered.

	* `st2/contrib/examples`
	* `st2/contrib/tests`
	* `st2/contrib/hello-st2`

See [`st2/st2common/packaging`](../st2common/packaging) to figure where and how it is all installed.
