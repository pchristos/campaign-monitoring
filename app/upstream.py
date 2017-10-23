"""Set of convenience methods to interact with the createsend API."""

import createsend

from django.conf import settings

from .models import CampaignList
from .models import CampaignClient
from .models import CampaignSubscriber


CS_AUTH = {'api_key': settings.API_KEY}


def get_client_details(client_id):
    """Fetch client details from Campaign Monitoring.

    Arguments:
        client_id   the ClientID assigned by Campaign Monitoring

    """
    client = createsend.Client(CS_AUTH, client_id=client_id)
    return client.details().BasicDetails()


def sync_client(client_id):
    """Fully sync upstream data of a Campaign Monitorig Client.

    Fetches and stores locally client details, campaigns lists,
    and subscribers.

    Arguments:
        client_id   the ClientID assigned by Campaign Monitoring

    """
    details = get_client_details(client_id)
    client = CampaignClient()
    client.name = details.ContactName
    client.email = details.EmailAddress
    client.company = details.CompanyName
    client.country = details.Country
    client.external_id = details.ClientID
    client.save()
    sync_client_lists(client)
    return client


def get_client_lists(client):
    """Yield the client's campaign lists.

    Arguments:
        client   an instance of `.models.CampaignClient`

    """
    cs = createsend.Client(CS_AUTH, client_id=client.external_id)
    for clist in cs.lists():
        yield clist


def sync_client_lists(client):
    """Fetch a client's lists and store them locally.

    Arguments:
        client   an instance of `.models.CampaignClient`

    """
    for upstream_list in get_client_lists(client):
        clist = CampaignList()
        clist.client = client
        clist.name = upstream_list.Name
        clist.external_id = upstream_list.ListID
        clist.save()
        sync_list_subscribers(clist)


def get_list_subscribers(clist):
    """Yield all the subscribers of a campaign list.

    Arguments:
        clist   an instance of `.models.CampaignList`

    """
    upstream_clist = createsend.List(CS_AUTH, clist.external_id)
    for status in settings.SYNC_STATUS:
        for subscriber in getattr(upstream_clist, status)().Results:
            yield subscriber


def sync_list_subscribers(clist):
    """Store subscriber details.

    Arguments:
        clist   an instance of `.models.CampaignList`

    """
    for upstream_subscriber in get_list_subscribers(clist):
        subscriber = CampaignSubscriber()
        # We need to save before being able to create a m2m relationship.
        subscriber.save()
        subscriber.lists.add(clist)
        subscriber.name = upstream_subscriber.Name
        subscriber.email = upstream_subscriber.EmailAddress
        subscriber.state = upstream_subscriber.State
        subscriber.save()


def import_subscriber(list_id, custom_fields=None, resubscribe=True, **params):
    """Import a subscriber to an existing list.

    Arguments:
        list_id    the ListID assigned by Campaign Monitoring
        params     parameters required to import a new subscriber

    """
    subscriber = createsend.Subscriber(CS_AUTH, list_id=list_id)
    subscriber.add(list_id=list_id, custom_fields=custom_fields,
                   resubscribe=resubscribe, **params)


def delete_subscriber(list_id, email):
    """Delete an existing subscriber from a list.

    Arguments:
        list_id    the ListID assigned by Campaign Monitoring
        email      the e-mail address of the subscriber to delete

    """
    subscriber = createsend.Subscriber(
        CS_AUTH, list_id=list_id, email_address=email
    )
    subscriber.delete()
