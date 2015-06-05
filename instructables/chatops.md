Hi, and thanks for helping us try out our ChatOps beta. We value your feedback, and would love to hear it. Please send us a note at `support@stackstorm.com`, or come chat with us on IRC at irc://irc.freenode.net/#stackstorm.

## What is ChatOps

ChatOps is a new operational paradigm where work that is already happening in the background today is brought into a common chatroom. By doing this, you are unifying the communication about what work should get done with actual history of the work being done. Things like deploying code from chat, viewing graphs from a TSDB or logging tool, or creating new Jira tickets... all of these are examples of tasks that can be done via ChatOps.

Not only does ChatOps reduce the feedback loop of work output, it also empowers others to accomplish complex self-service tasks that they otherwise would not be able to do. Combining ChatOps and StackStorm is an ideal combination, where from Chat users will be able to execute actions and workflows to accelerate the IT delivery pipeline.

Excited to try it out? Let's do it!

## Getting Started

In effort to make setup as quick and easy as possible, we have setup our `st2workroom` environment to allow you to spin up a test copy of StackStorm with ChatOps to kick the tires around. This installation has all of the necessary bits configured, including basic Hubot and Pack deployment management. Once this is done, we need to configure the workroom to download the most up-to-date code. Next, we'll configure HuBot to connect to your Chat Room and StackStorm. Finally, we'll show you how to enable start setting up ChatOps actions.

### Vagrant Setup

To get started, you will need a few software projects. They are:

* Vagrant: https://www.vagrantup.com/downloads.html
* VirtualBox: https://www.virtualbox.org/wiki/Downloads


This project is used to help provide a consistent experience for people testing, experimenting, developing with, or developing against StackStorm. For more info on this project and how it is used, please take a look at http://stackstorm.com/2015/04/03/rapid-integration-development-with-stackstorm/.

To get started, first download the `st2workroom`.

```
$ mkdir ~/stackstorm
$ git clone https://github.com/StackStorm/st2workroom ~/stackstorm/st2workroom
$ cd ~/stackstorm/st2workroom
```

Then, let's configure the workroom. We'll first configure the stack. This defines where StackStorm will look for its integration packs. Open up the file `stacks/st2.yaml` with your favorite editor. You should configure it to look like this:

```
# stacks/st2.yaml
---
# Defaults can be defined and reused with YAML anchors
defaults: &defaults
  domain: stackstorm.net
  memory: 1024
  cpus: 1
  box: puppetlabs/ubuntu-14.04-64-puppet
st2express:
  <<: *defaults
  hostname: st2express
  private_networks:
    - 172.168.200.10
  sync_type: nfs
  puppet:
    facts:
      role: st2express
  mounts:
    - "/opt/stackstorm/packs:artifacts/packs"
```

This will setup StackStorm to store all pack files and chatops aliases in the `artifacts/packs` directory at the root of the workroom. This will allow you to edit files using your favorite editor on your computer.

Now, let's setup the contents of the workroom. Create the workroom config file by starting with the example template.

```
$ cd ~/stackstorm/st2workroom
$ cp hieradata/workroom.yaml.example hieradata/workroom.yaml
```

Open up the file `hieradata/workroom.yaml` in your favorite text editor. In here, you will setup the configuration version of StackStorm, and Hubot. In this file, set the following values:

```yaml
# hieradata/workroom.yaml
---
st2::version: 0.10.0
st2::mistral_git_branch: st2-0.10.0
```

Next, configure Hubot. Take a look at the commented lines. At the minimum, you must provide:

* `hubot::adapter`:
  * Take a look at the options Hubot has to connect to at https://github.com/github/hubot/blob/master/docs/adapters.md.
  * Make note of which chat client you use, and navigate to https://npmjs.com and search for your adapter (hubot-slack for example)
* `hubot::env_export`:
  * A list of key/value pairs to inject into Hubot's running environment.
* `hubot::dependencies`:
  * This is where you will define which version of Hubot to run, which version of hubot-scripts, and any adapters you need to install.
    At the very least, you need to specify ``hubot-stackstorm`` adapter.

As an example, here is what configuration looks like for a Hubot Slack

```yaml
# hieradata/workroom.yaml
---
hubot::chat_alias: "!"
hubot::adapter: "slack"
hubot::env_export:
 HUBOT_LOG_LEVEL: "debug"
 HUBOT_SLACK_TOKEN: "xoxb-XXXX"
 EXPRESS_PORT: 8081
 ST2_CHANNEL: "hubot"
hubot::external_scripts:
  - "hubot-stackstorm"
hubot::dependencies:
  - "hubot": ">= 2.6.0 < 3.0.0"
  - "hubot-scripts": ">= 2.5.0 < 3.0.0"
  - "hubot-slack": ">=3.3.0 < 4.0.0"
  - "hubot-stackstorm": ">= 0.1.0 < 0.2.0"
```

Take note of the `EXPRESS_PORT` environment variable. Hubot's HTTP port in `st2workroom` needs to be moved to `TCP 8081` to avoid port conflict with `st2web`, which serves on `TCP 8080`. If you are not running your bot on the same machine where StackStorm is running, you can omit this variable. Pay attention to this information, however, as it is needed in order to configure a callback from StackStorm.

By default, Hubot connects to StackStorm on `localhost`. If you install your bot on a machine other than where StackStorm is deployed, set the following variables:

```
 ST2_API: http://st2api.yourcomany.net:9101
 ST2_AUTH: http://st2auth.yourcompany.net:9100
```

To obtain Slack auth token, you need add new Slack integration by going to
https://<yourcompany>.slack.com/services/new/hubot.

If you have authentiation enabled, you also need to specify `ST2_AUTH_USERNAME` and `ST2_AUTH_PASSWORD` environment variable.

After all this is setup, start up the workroom.

```
$ vagrant up
```

At any point, you can SSH into this node by navigating to the `~/stackstorm/st2workroom` directory, and executing the command `vagrant ssh`.

This process will take a few minutes, and when completed, a new Hubot should be sitting in your Chat room ready to accept and send commands to StackStorm. Proceed to the section [Configure Stackstorm](#configuring-stackstorm) to continue.

### Manual Installation

To get started, you will need:

* StackStorm v0.10dev
* Hubot
* StackStorm Hubot adapter

First, start by updating your version of StackStorm. This is typically done by re-running `st2_deploy.sh` with the updated version code.

```
$ st2_deploy.sh 0.10dev
```

Now, take a moment to also install and configure Hubot. Instructions on how to configure and deploy Hubot for your platform can be found [here](https://hubot.github.com/docs/deploying/). Also ensure it is configured to connect to your chat service of choice. You can find documentation for this at https://github.com/github/hubot/blob/master/docs/adapters.md.

Finally, you need to install and configure StackStorm Hubot plugin. For information on
how to do that, please visit the following page - [Installing and configuring the plugin](https://github.com/stackstorm/hubot-stackstorm#installing-and-configuring-the-plugin).

If you are installing Hubot on a machine that is not the same as your StackStorm installation, you will need to set the following environment variables:

* `ST2_API` - FQDN + port to StackStorm endpoint. Typically: `http://<host>:9101`

Once done, start up your Hubot instance. Validate that things are working alright and Hubot is connecting to your client by issuing a default command. For example, if you named your Hubot instance `frybot`, you can issue the command:

```
  frybot: the rules
```

And should get something like this back:

![slack](https://cloud.githubusercontent.com/assets/20028/7257451/24387d24-e856-11e4-856b-b9f457f002b0.png)

Now, install the `hubot` pack into your StackStorm installation.

```
  $ st2 packs.install packs=hubot
```

If successful, proceed to the section [Configure Stackstorm](#configuring-stackstorm) to continue.

### Configuring StackStorm

At this point, it is necessary to introduce a few new terms as it relates to how ChatOps messages are processed internally. First, you will need to create a _notification_ rule. This will leverage the new notifications system, and allow us to send messages back to Hubot. Then, you will configure _aliases_ which map commands from Hubot to actions in StackStorm. Finally, you'll configure actions to use the _notifications_, thus completing the entire chain of events. Let's get started.

First, let's configure our global notification rule. To do this, let's create a new pack in StackStorm called `chatops`. Navigate to the `artifacts/packs` directory, and create a new pack directory.

```
$ cd ~/stackstorm/st2workroom/artifacts/packs
$ mkdir -p chatops/{actions,rules,sensors,aliases}
```

Now, let's configure an alias and setup an action to be used in ChatOps. For this example, I am going to download a pack from our `st2contrib` repository, the Google pack. This will provide us with the action `google.get_search_results` that we will expose via ChatOps. First, SSH into the vagrant machine and install the pack.

```
$ cd ~/stackstorm/st2workroom
$ vagrant ssh
$ st2 run packs.install packs=google
```

Now, let's setup an alias. For purpose of this setup aliases are stored in the directory `/opt/stackstorm/packs/chatops/aliases` on the filesystem. From your host filesystem, you can access them from `~/stackstorm/st2workroom/artifacts/packs/chatops/aliases`. We have already created this directory in a previous step.

```
$ cd ~/stackstorm/st2workroom
$ cd artifacts/packs/chatops/aliases
```

Create a new file called `google.yaml`, and add the following contents.

```yaml
# packs/chatops/aliases/google.yaml
---
name: "google_query"
action_ref: "google.get_search_results"
formats:
  - "google {{query}}"
```

Now, navigate to the hubot pack `rules` directory, and view the notify_hubot rule. This is a notification rule that sets up a notification channel.

```
$ cd ~/stackstorm/st2workroom/artifacts/packs/hubot/rules
$ vi notify_hubot.yaml
```

That rule, looks as follows:

```yaml
# notify_hubot.yaml
---
name: "chatops.notify_hubot"
enabled: true
description: "Notification rule to send messages to Hubot"
trigger:
  pack: "chatops"
  type: "core.st2.generic.notifytrigger"
criteria:
  trigger.channel:
    pattern: "hubot"
    type: "equals"
action:
  ref: hubot.post_result
  parameters:
    channel: "{{trigger.data.source_channel}}"
    user: "{{trigger.data.user}}"
    result: "{{trigger}}"
```

This file is also here to serve as an example on how to setup other notification triggers.

Now, once this is all done, register all the new files we created and reload Hubot. Do this with the following commands:

```
$ cd ~/stackstorm/st2workroom
$ vagrant ssh -- sudo st2ctl reload --register-all
$ vagrant ssh -- sudo st2ctl restart
$ vagrant ssh -- sudo service hubot restart

```

This will register the aliases we created, and tell Hubot to go and refresh its command list.

You should now be able to go into your chatroom, and execute the command `hubot: google awesome`, and StackStorm will take care of the rest.

![slack](https://cloud.githubusercontent.com/assets/20028/7208555/6a7e74e8-e507-11e4-8ebd-02b650beee46.png)

That's it! Now, you should be able to begin converting actions of all kinds to be ChatOps capable. Go ahead and give the system a shot, and do not be afraid to provide feedback on things that you like and things that can make your experience better. As we learn more about ChatOps and add additional features, we will be updating this document, so stay tuned for hints, tips, and additional features coming over the next few weeks.

Happy ChatOps-ing!
