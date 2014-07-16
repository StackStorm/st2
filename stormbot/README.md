Stormbot
========

This is a version of GitHub's Campfire bot, hubot. He's pretty cool. Blah-blah-blah...

### Testing Stormbot Locally

You can test your hubot by running the following.

    % bin/hubot

You'll see some start up output about where your scripts come from and a prompt.

    [Sun, 04 Dec 2011 18:41:11 GMT] INFO Loading adapter shell
    [Sun, 04 Dec 2011 18:41:11 GMT] INFO Loading scripts from /home/tomb/Development/hubot/scripts
    [Sun, 04 Dec 2011 18:41:11 GMT] INFO Loading scripts from /home/tomb/Development/hubot/src/scripts
    Hubot>

Then you can interact with hubot by typing `hubot help`.

    Hubot> hubot help

    Hubot> Hubot command count - Tells how many commands Hubot knows
    Hubot execute <command> [<argument>, ...] - calls out to run the shell staction.
    Hubot execute anaction [command] - Action that executes an arbitrary Linux command.
    ...

### Running Stormbot in Hipchat

To make bot to connect to Hipchat, just run the following command.

    % bin/hubot-hipchat

Right now, all its credentials are hardcoded inside the file. Eventually we would probably need to
find a way to store them externally in config file of some sort.
