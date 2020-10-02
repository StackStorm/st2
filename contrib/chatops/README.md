# chatops integration pack v1.1.0

> ChatOps integration pack
StackStorm, Inc. <info@stackstorm.com>

### Contributors
- Anthony Shaw <anthonyshaw@apache.org>
- Carlos <nzlosh@yahoo.com>


## Actions


The pack provides the following actions:

### post_message
_Post a message to stream for chatops_

| Parameter | Type | Required | Secret | Description |
|---|---|---|---|---|
| `experimental` | n/a | default | default | _Unavailable_ |
| `route` | string | default | default | _Text to represent a routing key.  Use to identify annoncement events in the Stream API._ |
| `user` | string | default | default | _Explicitly notify a user_ |
| `whisper` | boolean | default | default | _Send a private message to user_ |
| `message` | string | True | default | _Message to send._ |
| `channel` | string | True | default | _Channel to post to_ |
| `context` | object | False | default | _Context for channel (includes type of channel, user, etc.)_ |
| `extra` | object | default | default | _Extra adapter-specific parameters._ |
### match
_Match a string to an action alias_

| Parameter | Type | Required | Secret | Description |
|---|---|---|---|---|
| `text` | string | True | default | _The text to match_ |
### run
_Match a text chatops command, execute it and post the result_

| Parameter | Type | Required | Secret | Description |
|---|---|---|---|---|
| `user` | string | default | default | _Explicitly notify a user_ |
| `whisper` | boolean | default | default | _Send a private message to user_ |
| `text` | string | True | default | _Chatops command_ |
| `channel` | string | True | default | _Channel to post to_ |
### match_and_execute
_Execute a chatops string to an action alias_

| Parameter | Type | Required | Secret | Description |
|---|---|---|---|---|
| `text` | string | True | default | _The text to match_ |
| `source_channel` | string | False | default | _The source channel to set on the execution_ |
| `user` | string | False | default | _User ID calling the command_ |
### format_execution_result
_Format an execution result for chatops_

| Parameter | Type | Required | Secret | Description |
|---|---|---|---|---|
| `execution_id` | string | True | default | _Id of execution to format_ |
### post_result
_Post an execution result to stream for chatops_

| Parameter | Type | Required | Secret | Description |
|---|---|---|---|---|
| `user` | string | default | default | _Explicitly notify a user_ |
| `whisper` | boolean | default | default | _Send a private message to user_ |
| `execution_id` | string | True | default | _ID of an execution to send_ |
| `channel` | string | True | default | _Channel to post to_ |
| `route` | string | default | default | _Text to represent a routing key.  Use to identify annoncement events in the Stream API._ |
| `context` | object | False | default | _Context for channel (includes type of channel, user, etc.)_ |



## Sensors

There are no sensors available for this pack.



## Legal

Obligatory kudos to https://icons8.com/ for the icon.

<sub>Documentation generated using [pack2md](https://github.com/nzlosh/pack2md)</sub>