CloudSlang
==========
`CloudSlang <http://cloudslang.io>`_ is a open source orchestration tool for managing deployed applications. It allows you to rapidly automate your DevOps and everyday IT operations use cases.

The CloudSlang language is a YAML-based DSL for writing workflows. Using CloudSlang you can define a workflow in a structured, easy-to-understand format.

There are two main types of CloudSlang content, operations and flows. An operation contains an action, which can be written in Python or Java. Operations perform the “work” part of the workflow. A flow contains tasks, which stitch together the actions performed by operations, navigating and passing data from one to the other based on operation results and outputs. Flows perform the “flow” part of the workflow.

The CloudSlang project also includes a `repository <https://github.com/CloudSlang/cloud-slang-content>`_ of ready-made content to perform common tasks as well as content that integrates with many of today’s hottest technologies, such as Docker and CoreOS.

Simple Workflow
+++++++++++++++
The following is a simple example to give you an idea of how CloudSlang flows and operations are structured:

**Flow**

.. sourcecode:: YAML

    namespace: examples.hello_world
    
    imports:
         ops: examples.hello_world
    
    flow:
        name: hello_world
        workflow:
            - sayHi:
                do:
                    ops.print:
                        - text: "'Hello, World'"

**Operation**
 
.. sourcecode:: YAML

    namespace: examples.hello_world
    
    operation:
        name: print
        inputs:
            - text
        action:
            python_script: print text
        results:
            - SUCCESS
			
For more information on composing CloudSlang content, see the CloudSlang `documentation <http://www.cloudslang.io/#/docs>`_, the CloudSlang `tutorial <http://cloudslang-tutorials.readthedocs.org/>`_ and the introductory `video <https://www.youtube.com/watch?v=CX1_It_Ygso>`_.