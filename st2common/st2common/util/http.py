import six

http_client = six.moves.http_client

HTTP_SUCCESS = [http_client.OK, http_client.CREATED, http_client.ACCEPTED,
                http_client.NON_AUTHORITATIVE_INFORMATION, http_client.NO_CONTENT,
                http_client.RESET_CONTENT, http_client.PARTIAL_CONTENT,
                http_client.MULTI_STATUS, http_client.IM_USED,
                ]
