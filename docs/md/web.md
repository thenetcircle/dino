## GET /api/spam

Get the latest messages classified as spam.

```bash
user@box:~$ curl -X GET localhost:4556/api/spam
```

Response would be something similar to the following:

```json
{
	"data": [{
		"correct": true,
		"from_id": "126144",
		"from_name": "fuyfuyf",
		"id": 8,
		"message": "\ud835\udd4e\ud835\udd3c\ud835\udd4e\ud835\udd5a\ud835\udd43\ud835\udd43\ud835\udd4a\ud835\udd4b\ud835\udd3b\ud835\udd4c",
		"message_deleted": true,
		"message_id": "42957c6c-6290-4744-8e79-8c6e3fe7319b",
		"object_type": "room",
		"probability": "0.932408,0.98,1",
		"time_stamp": 1535312965,
		"to_id": "126144",
		"to_name": "fdsa"
	}, {
		"correct": true,
		"from_id": "126144",
		"from_name": "fuyfuyf",
		"id": 7,
		"message": "gfdhgdf",
		"message_deleted": true,
		"message_id": "75550bd5-faa8-4393-b8da-65141f46898c",
		"object_type": "room",
		"probability": "0.81171554,0.99,1",
		"time_stamp": 1535312962,
		"to_id": "126144",
		"to_name": "fdsa"
	}],
	"message": "",
	"status_code": 200
}
```

## POST /api/spam/search

Search for spam messages given a time range and either a room uuid or user ID of a sender.

```bash
user@box:~$ curl -X POST localhost:4556/api/spam/search -H 'Content-Type: application/json' -d '{"room":"9fa5b40a-f0a6-44ea-93c1-acf2947e5f09","from":"2018-08-26T04:00:00Z","to":"2018-08-27T04:00:00Z"}'
```

Response would be something similar to the following:

```json
{
	"data": [{
		"correct": true,
		"from_id": "126144",
		"from_name": "fuyfuyf",
		"id": 8,
		"message": "\ud835\udd4e\ud835\udd3c\ud835\udd4e\ud835\udd5a\ud835\udd43\ud835\udd43\ud835\udd4a\ud835\udd4b\ud835\udd3b\ud835\udd4c",
		"message_deleted": true,
		"message_id": "42957c6c-6290-4744-8e79-8c6e3fe7319b",
		"object_type": "room",
		"probability": "0.932408,0.98,1",
		"time_stamp": 1535312965,
		"to_id": "126144",
		"to_name": "fdsa"
	}, {
		"correct": true,
		"from_id": "126144",
		"from_name": "fuyfuyf",
		"id": 7,
		"message": "gfdhgdf",
		"message_deleted": true,
		"message_id": "75550bd5-faa8-4393-b8da-65141f46898c",
		"object_type": "room",
		"probability": "0.81171554,0.99,1",
		"time_stamp": 1535312962,
		"to_id": "126144",
		"to_name": "fdsa"
	}],
	"message": "",
	"status_code": 200
}
```

## GET /api/spam/<spam_id>

Get one spam message.

Request:

```bash
user@box:~$ curl -X GET localhost:4556/api/spam/3
```

Response:

```json
{
	"data": {
		"correct": true,
		"from_id": "115584",
		"from_name": "",
		"id": 3,
		"message": "\ud835\udd4e\ud835\udd3c\ud835\udd4e\ud835\udd5a\ud835\udd43\ud835\udd43\ud835\udd4a\ud835\udd4b\ud835\udd3b\ud835\udd4c",
		"message_deleted": false,
		"message_id": "21aa49f3-3dc5-4bef-a08d-84f7a516bf49",
		"object_type": "room",
		"probability": "0.932408,0.98,1",
		"time_stamp": 1535309860,
		"to_id": "115584",
		"to_name": "jkvkjvh"
	},
	"message": "",
	"status_code": 200
}
```

## POST /api/spam/<spam_id>/incorrect

Set a spam message as incorrectly classified. The `correct` flag on this spam messages will be `false` after this.

Request:

```bash
user@box:~$ curl -X POST localhost:4556/api/spam/3/incorrect
```

Response:

```json
{
	"data": {},
	"message": "",
	"status_code": 200
}
```

## POST /api/spam/<spam_id>/correct

Set a spam message as correctly classified. The `correct` flag on this spam messages will be `true` after this.

Request:

```bash
user@box:~$ curl -X POST localhost:4556/api/spam/3/correct
```

Response:

```json
{
	"data": {},
	"message": "",
	"status_code": 200
}
```

## POST /api/spam/enable

Enable the spam classifier. 

When enabled, the classifier will prevent messages being broadcasted that has been classified as spam. If disabled, it will still classify them, but it won't prevent them from being broadcasted.

Request:

```bash
user@box:~$ curl -X POST localhost:4556/api/spam/enable
```

Response:

```json
{
	"data": {},
	"message": "",
	"status_code": 200
}
```

## POST /api/spam/disable

Disable the spam classifier. 

When enabled, the classifier will prevent messages being broadcasted that has been classified as spam. If disabled, it will still classify them, but it won't prevent them from being broadcasted.

Request:

```bash
user@box:~$ curl -X POST localhost:4556/api/spam/disable
```

Response:

```json
{
	"data": {},
	"message": "",
	"status_code": 200
}
```

## GET /api/spam/isenabled

Check if the spam classifier is enabled or not. 

When enabled, the classifier will prevent messages being broadcasted that has been classified as spam. If disabled, it will still classify them, but it won't prevent them from being broadcasted.

Request:

```bash
user@box:~$ curl -X GET localhost:4556/api/spam/isenabled
```

Response:

```json
{
	"data": {},
	"message": "enabled",
	"status_code": 200
}
```

Example:

```bash
user@box:~$ curl -X POST localhost:4556/api/spam/disable
{
	"data": {},
	"message": "",
	"status_code": 200
}
user@box:~$ curl -X GET localhost:4556/api/spam/isenabled
{
	"data": {},
	"message": "disabled",
	"status_code": 200
}
user@box:~$ curl -X POST localhost:4556/api/spam/enable
{
	"data": {},
	"message": "",
	"status_code": 200
}
user@box:~$ curl -X GET localhost:4556/api/spam/isenabled
{
	"data": {},
	"message": "enabled",
	"status_code": 200
}
```

## Deleting a message classified as spam

The `message_id` field describes the ID of the message stored in the message store. It can be deleted by using the history web API:


```bash
user@box:~$ curl -X GET localhost:4556/api/spam/3
{
	"data": {
		"correct": true,
		"from_id": "115584",
		"from_name": "",
		"id": 3,
		"message": "\ud835\udd4e\ud835\udd3c\ud835\udd4e\ud835\udd5a\ud835\udd43\ud835\udd43\ud835\udd4a\ud835\udd4b\ud835\udd3b\ud835\udd4c",
		"message_deleted": false,
		"message_id": "21aa49f3-3dc5-4bef-a08d-84f7a516bf49",
		"object_type": "room",
		"probability": "0.932408,0.98,1",
		"time_stamp": 1535309860,
		"to_id": "115584",
		"to_name": "jkvkjvh"
	},
	"message": "",
	"status_code": 200
}
user@box:~$ curl -X DELETE localhost:4556/api/history/21aa49f3-3dc5-4bef-a08d-84f7a516bf49
{
	"data": {},
	"message": "",
	"status_code": 200
}
user@box:~$ curl -X GET localhost:4556/api/spam/3
{
	"data": {
		"correct": true,
		"from_id": "115584",
		"from_name": "",
		"id": 3,
		"message": "\ud835\udd4e\ud835\udd3c\ud835\udd4e\ud835\udd5a\ud835\udd43\ud835\udd43\ud835\udd4a\ud835\udd4b\ud835\udd3b\ud835\udd4c",
		"message_deleted": true,
		"message_id": "21aa49f3-3dc5-4bef-a08d-84f7a516bf49",
		"object_type": "room",
		"probability": "0.932408,0.98,1",
		"time_stamp": 1535309860,
		"to_id": "115584",
		"to_name": "jkvkjvh"
	},
	"message": "",
	"status_code": 200
}
```

# Probability

The field `probability` are percentages from three different classifiers. If at least two of them predict with a percentage of at least 66% that a message is spam, then it will be labeled as such.

The first number is from XGBoost, the second from a Random Forest, and the third SVC with a polynomial kernel. The third number is always either `0` or `1`, and never a fraction.
