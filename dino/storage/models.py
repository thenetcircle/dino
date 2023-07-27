from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model


class Messages(Model):
    __table_name__ = "messages"

    target_id = columns.Text(
        primary_key=True
    )
    from_user_id = columns.Text(
        primary_key=True,
        clustering_order="ASC"
    )
    sent_time = columns.Text(
        primary_key=True,
        clustering_order="ASC"
    )
    time_stamp = columns.Integer(
        primary_key=True,
        clustering_order="ASC"
    )

    body = columns.Text()
    channel_id = columns.Text()
    channel_name = columns.Text()
    deleted = columns.Boolean()
    domain = columns.Text()
    from_user_name = columns.Text()
    message_id = columns.Text()
    target_name = columns.Text()
