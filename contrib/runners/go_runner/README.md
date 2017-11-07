Go Runner
=========

This runner allows native Go code to be compiled and run as actions, allowing Go source to be distributed in packs.

VERY MUCH A WIP - consider this wholly unstable for the time being

# TODOs

- Lock down the dependency management strategy
- Tests
- Standardize output (gonna be JSON, just need to document the "proper" way to do this)
- Figure out GOPATH management. You'll have to do something like GOPATH=$GOPATH:/Users/oswaltm/Code/Python/stackstorm-goexamples when compiling - will the user have to do this for any reason?
- Need to figure out how arguments are passed into action
- publish your example pack to your repo

# Dependency Management

This runner offers two options for running Go programs:

- Run your Go programs like a script, like `go run this_action.go`. This means any external code that your program uses must be in the standard Go library, or installed outside the pack and findable via GOPATH
- Structure your Go programs in such a way where code is vendored in the pack itself. In this case, your program must have a start point in `cmd/` and dependencies vendored using `vendor/`

# Requirements

Need to have a reasonable Go installation (i.e. go binaries on the PATH, and GOPATH set up). This runner will attempt to "go install" the actions before running them - therefore, the GOPATH must be set, and $GOPATH/bin must be on the path.

