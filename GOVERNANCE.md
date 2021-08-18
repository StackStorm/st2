StackStorm has joined Linux Foundation in 2019.
With the new Neutral Home we invite everyone: organizations, teams and individuals relying on StackStorm Automation in their operations to support the project by giving back and participating in development as well as influence on its future under the Open Governance.

# StackStorm Governance
This document defines governance policies for the StackStorm project.
It extends [Technical Charter](https://stackstorm.com/wp/wp-content/uploads/2020/06/2019-09-03-StackStorm-Project-Technical-Charter.pdf) for StackStorm within the Linux Foundation.

## Technical Steering Committee (TSC)
The Technical Steering Committee is a group of Maintainers (Committers) who have earned the ability to modify (“commit”) sourcecode, documentation or other artifacts.
This group is responsible for all technical oversight of StackStorm as Open Source Project.

### Maintainer Roles
The current list of maintainers is published and updated in [OWNERS.md](OWNERS.md).
StackStorm uses a three-tiered system of Maintainer roles:
* [Leaders](OWNERS.md#leaders-)
  * Head of Technical Steering Committee (TSC).
  * Responsible for Project Strategy, External Relations, Organizational aspects, coordinating Events, Partnerships.
  * Receive **three votes** in the [conflict resolution and voting process](#conflict-resolution-and-voting) described below.
* [Senior Maintainers](OWNERS.md#senior-maintainers-)
  * Have the most in-depth experience with the StackStorm project and are expected to have the knowledge and insight to lead the project's future, growth, standards and improvement.
  * Oversee the process for adding new maintainers and provide guidance, help and sharing their experience with the standard maintainers.
  * Have full owner access to all the resources and platforms that sustain StackStorm project.
  * Receive **two votes** in the voting process.
* [Maintainers](OWNERS.md#maintainers-)
  * Have good experience with the StackStorm codebase, expected to provide significant value to the project, helping it grow, improve and succeed.
  * Have full member write access to [StackStorm](https://github.com/stackstorm/) and [StackStorm-Exchange](https://github.com/stackstorm-exchange) Github organizations, CI/CD, Moderator at [forum](https://forum.stackstorm.com/), [Slack](https://stackstorm.com/community-signup) and other Community platforms.
  * Receive **one vote** in the voting process.

### Maintainer Activities
* Monitor one or more of: Slack, Forums, and other Communication channels with StackStorm Community (delayed response is perfectly acceptable).
* Attend the Community meetings to discuss the project plans, roadmap and commitments.
* Triage GitHub issues and perform pull request reviews for [StackStorm](https://github.com/stackstorm/) and [StackStorm-Exchange](https://github.com/stackstorm-exchange/) Github organizations.
  The areas of specialization listed in [OWNERS.md](OWNERS.md) can be used to help with routing
  an issue/question to the right person.
* During GitHub issue triage, apply all applicable [labels](https://github.com/StackStorm/st2/labels)
  to each new issue. Labels are extremely useful for future issue follow up. A few of the most important labels that are
  not self explanatory are:
  * **good first issue**: Mark any issue that can reasonably be accomplished by a new contributor with this label. It's important to lower the barrier of entry and leave first tasks for new contributors.
  * **help wanted**: Unless it is immediately obvious that someone is going to work on an issue (and if so assign it), mark it help wanted.
  * **status:to be verified**: If the reported bug needs to be confirmed before working on a fix.
  * **status:need more info**: If the issue needs more information from someone who reported it.
  * see all the Github [**labels**](https://github.com/stackstorm/st2/labels). Recommended informative balance for the issue is 3-5 labels.
* Make sure that ongoing PRs are moving forward at the right pace or closing them. It's important to apply the same to old PRs and Issues to retain healthy project state.
* Guide Community about using the right channel: Github for Issues and Bug-reports, while Forums and Slack for questions and discussions.
* Project maintenance: security, updates, CI/CD, builds, infrastructure.
* Prioritize the work following [StackStorm Roadmap](https://docs.stackstorm.com/latest/roadmap.html) to move the project forward.
* All maintainers ideally are expected to shoulder a proportional share of community work: Issues, Reviews, Slack, Forum, Releases, fixing CI/CD Builds, etc. Work upon to make sure the balance is kept within the team.
* Encourage and guide other community members to contribute back to StackStorm. Even a simple bug report or a one-line documentation PR is a win!
* Follow-up by filing undocumented issues found in community channels, show an example.
* Share the experience with other Maintainers and Contributors.

## Becoming a Maintainer
Any level of contribution is welcomed: starting from feedback, reporting bugs, manually verifying features and fixes, improving documentation, helping other community members ending with the actual code, PRs, writing tests, reviews, fixes, proposing architecture or even marketing efforts.

### How to start Contributing?
* Start helping StackStorm is easy. A few contributing activities that are highly valued:
  * answer user questions and troubleshoot issues in Community: Slack, Forums, Github
  * triaging issues with [**status: to be verified**](https://github.com/stackstorm/st2/issues?q=is%3Aissue+is%3Aopen+status+label%3A%22status%3Ato+be+verified%22) will help you to get familiar with the project functionality
  * working on issues tagged as [**good first issue**](https://github.com/StackStorm/st2/contribute)
  * [**bugs**](https://github.com/stackstorm/st2/issues?q=is%3Aissue+is%3Aopen+status+label%3Abug) are very important to address and will help you to get more familiar with the codebase
  * enhancements marked with [**refactoring**](https://github.com/stackstorm/st2/issues?q=is%3Aopen+is%3Aissue+label%3Arefactor) tag
  * any [documentation](https://github.com/stackstorm/st2docs) improvements are always appreciated
  * perform code reviews on other's pull requests. Second pair of eyes and a few cycles of manual testing can help to prevent bugs early
  * join the *#development* channel in [StackStorm Slack](https://stackstorm.com/#community) for more pointers from the current Maintainers
  * help growing community ecosystem by writing technical content about StackStorm like HOWTOs, Show Cases and Demos, Blog posts, Tutorials. We also accept [guest posts](https://stackstorm.com/blog/)!
* After period of time you will be proposed to be added to the Contributors group of [OWNERS.md](OWNERS.md#contributors).

### How to become a Maintainer?
Besides of activities listed in Contributing section, you need to demonstrate a strong commitment to the long term success of a project.
Just contributing does not make you a maintainer, it is about building trust with the current maintainers of the project and being a person that they can depend on and trust to make decisions in the best interest of StackStorm.

Periodically, the existing maintainers curate a list of contributors that have shown regular activity on the project over the prior months. From this list, maintainer candidates are selected and proposed.
* Becoming a maintainer generally means that you are going to be spending substantial time (at least 1 full day/week) on StackStorm for the foreseeable future.
* You should have ability to write a good solid code and collaborate with the team and community.
* Enough effort to understanding of the core project's code base (stackstorm/st2) and internals.
* Understanding of how the team works (policies, processes for testing, quality standards, code review, etc).
* Start doing PRs and code reviews under the guidance of maintainers: ask where the help is needed.
* As you gain experience with the code base and our standards, we will expect you to start working on increasingly complicated PRs, under the guidance of the existing maintainers.
* We may ask you to do some PRs from our backlog or roadmap. It's important to understand that as Maintainers we try to follow the common goals and plans.
* After a period of 3+ months of working together and making sure we see eye to eye, the existing maintainers will discuss granting "standard" maintainer access or not.
We make no guarantees on the length of time this will take, but 3+ months is the approximate time.
* Maintainers will be proposed to be added to the StackStorm GitHub organization and Maintainers group of [OWNERS.md](OWNERS.md) via voting.

### How to become a Senior Maintainer?
* Gain substantial in-depth experience with the codebase, project and processes.
* Manifest a major contribution to the project functionality.
* Demonstrate ability guiding other Maintainers and Contributors.
* Conduct at least one StackStorm release in a Maintainer role (release responsibility is rotated between the maintainers).
* "Standard" maintainer access can be upgraded via voting to "Senior" maintainer access after several months of work, depending on commitment and involvement.

## Removing a Maintainer
If a maintainer is no longer interested or cannot perform the maintainer duties listed above, they
should volunteer to be moved to non-voting Contributor or Friends status. In extreme cases this can also occur by a vote of
the maintainers per the voting process below.

## Conflict resolution and voting
In general, it's preferred that technical issues and maintainer membership are agreed
between the persons involved. If a dispute cannot be decided independently, the maintainers can be
called in to decide. If the maintainers themselves cannot decide an issue, the issue will
be resolved by voting.

## How decisions are made?
The process of adding, promoting or removing Contributors and Maintainers is done via composing a Pull Request (PR) against `OWNERS.md`
which includes details about contribution activities committed to the project during period of time and how that conforms with expected Maintainer responsibilities, skillset and the best interest of the project.
The decision is made based on TSC members votes in a PR.

The process of voting on other Issues, Proposals and Changes is performed by creating an open Github Discussion. For decisions making history reasons and to stimulate brainstorming, it's recommended to write a detailed research/description that covers possible outcomes and pros/cons behind the change to give comprehensive context.

Additions and removals of maintainers require a *2/3 majority*, while other decisions and changes
require only a simple majority. The voting period is one week.
