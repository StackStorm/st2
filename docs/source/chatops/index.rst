ChatOps
=======

What is it!?
------------

ChatOps provides a new way of collaboration and work within your teams. Boiled down to its essence, ChatOps represents _conversation-driven development_. With ChatOps, it is possible to take operational and development workflows and expose them as commands that can be executed in a company chat room. In doing so, you are unifying the communication about what work should get done with actual history of the work being done. Deploying code from chat, viewing graphs from a TSDB or logging tool, or creating new Jira tickets are all examples of tasks that can be done via ChatOps.

Not only does ChatOps reduce the feedback loop of work output, it also empowers others to accomplish complex, self-service tasks that they otherwise would not be able to do. Combining ChatOps and |st2| is an ideal combination, where from Chat users will be able to execute actions and workflows to accelerate the IT delivery pipeline. In the same way, the ChatOps/|st2|combination also enhances user adoption of automation through transparency and consistent execution.

The end result is improved agility and enhanced trust between teams. What’s not to love about this? It’s the reason we as a company are devoted to including it as a core part of our product.

TL;DR
-----

You're busy. We get it! We have an :doc:`./all_in_one` that is designed to get you up and running very quickly! Using this tool, you can seemlsessly install and configure ChatOps for many Chat Services. Head to the :doc:`./all_in_one` section, get setup, and then head back here once you're all finished!

Architecture
------------

.. figure:: /_static/images/chatops_architecture.png
    :align: center

    |st2| ChatOps Integration Overview

ChatOps leverages two components within |st2| in order to provide a fluid user experience. These subsystems are the :doc:`aliases` and :doc:`notification` subsystems. You can learn more about each of these individual components in their corresponding sub-sections.

|st2| flavored ChatOps
----------------------

Our goal with ChatOps is to take the patterns that are arising and make them consumable teams of all makeups. Behind our implementation of ChatOps lies the operational scalability and stability of |st2|, allowing you to grow and unleash the latent power of your existing teams. In addition to allowing integration with a plethora of existing plugins and patterns available in the larger |st2| and ChatOps communities, we add these features to the toolbelt:

* History and Audit. Get complete history and audit trails of all commands executed via ChatOps. Learn and understand how people are consuming the automation via ChatOps. Enhance your understanding.
* Workflow. Get real with workflow. Go beyond linear bash scripts and upgrade to parallel task execution.
* Bring your favorite tools! Each bot comes with it’s own requirement to learn their language. Forget that mess! Bring the tools that make you productive.

Our goal is to make ChatOps approachable by every team in every circumstance. This means an understanding of how teams of all sizes run, in many different types of verticals. Issues like compliance, security, reliability: these concerns are on forefront of our minds when we think about what ChatOps means to us, and how it provides real-world value to you.

Resources
---------

Interested in learning more? Here are some things to get you started on your voyage.

* `ChatOps: Technology and Philosophy <https://www.youtube.com/watch?v=IhzxnY7FIvg>`
* `Start automating with Slack <https://medium.com/why-not/what-will-the-automated-workplace-look-like-495f9d1e87da>`
* `Demonstration: See |st2| and ChatOps in action <https://www.youtube.com/watch?v=fUpSaEOS_BA>`
* `ChatOps for Dummies, Published by VictorOps <http://stackstorm.com/2015/04/23/stackstorm-and-chatops-for-dummies/>`
* `ChatOps and Event Driven Automation <https://www.youtube.com/watch?v=37LmuHToYjQ>`
* `ChatOps on Reddit <http://www.reddit.com/r/chatops>`
* `ChatOps on #freenode <http://webchat.freenode.net/?channels=##chatops>`

.. toctree::
    :maxdepth: 1

    chatops
    chatops-configuration
    aliases
    notifications
