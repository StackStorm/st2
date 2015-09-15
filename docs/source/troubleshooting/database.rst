Troubleshooting Database Issues
===============================

This section contains information on how to troubleshoot database (MongoDB) related issues.

Troubleshooting performance and missing index related issues
------------------------------------------------------------

If some of the API requests are slow you receive back "too much data" error, this could be caused
by an inefficient database query or a missing index.

To troubleshoot this issue, you should start the offending service (e.g. ``st2api``) with the
``--debug`` / ``--profile`` flag.

When this flag is used the service runs in the profiling mode meaning all the executed MongoDB
queries and related profiling information (which indexes were used, how many records / rows were
scanned, how long the query took, etc.) will be logged in the service log under the DEBUG log
level.
