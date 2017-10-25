from __future__ import unicode_literals

from django import forms
from django.db import models
from django.core.exceptions import ValidationError

from .upstream import import_subscriber
from .upstream import delete_subscriber


def validate_external_id(_id):
    """Validate a resource's external ID."""
    if not len(_id) is 32:
        raise ValidationError("Invalid external ID")


class CampaignClient(models.Model):
    """The base campaign client entity model.

    This class stores basic, high-level client information as retrieved
    from the Campaign Monitoring API.

    """

    email = models.EmailField(blank=True)
    name = models.CharField(max_length=64, blank=True)
    country = models.CharField(max_length=64)
    company = models.CharField(max_length=64)

    # The ClientID assigned by Campaign Monitoring. This is stored in
    # addition to the local db's pk.
    external_id = models.CharField(max_length=32, unique=True,
                                   validators=[validate_external_id])

    def save(self, *args, **kwargs):
        """Perform full validation and save."""
        self.full_clean()
        super(CampaignClient, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Delete self alongside all associated lists and subscribers."""
        for clist in self.campaignlist_set.all():
            for sub in clist.campaignsubscriber_set.all():
                sub.delete()
        super(CampaignClient, self).delete(*args, **kwargs)

    def __str__(self):
        return 'Client %s (%s)' % (self.name or self.company, self.external_id)


class CampaignList(models.Model):
    """A campaign list associated with a specific client.

    A campaign list groups subscribers logically together.

    """

    client = models.ForeignKey(CampaignClient, on_delete=models.CASCADE)

    name = models.CharField(max_length=64)
    external_id = models.CharField(max_length=32,
                                   validators=[validate_external_id])

    def subscribe(self, subscriber):
        """Add `subscriber` to self."""
        assert isinstance(subscriber, CampaignSubscriber)
        params = {'name': subscriber.name, 'email_address': subscriber.email}
        import_subscriber(self.external_id, **params)
        self.campaignsubscriber_set.add(subscriber)

    def unsubscribe(self, subscriber):
        """Remove `subscriber` from self."""
        assert isinstance(subscriber, CampaignSubscriber)
        delete_subscriber(self.external_id, subscriber.email)
        self.campaignsubscriber_set.remove(subscriber)

    def save(self, *args, **kwargs):
        """Perform full validation and save."""
        self.full_clean()
        super(CampaignList, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Delete a list and remove all of its subscribers."""
        for subscriber in self.campaignsubscriber_set.all():
            delete_subscriber(self.external_id, subscriber.email)
        super(CampaignList, self).delete(*args, **kwargs)

    def __str__(self):
        return 'List "%s" of %s' % (self.name, self.client)


class CampaignSubscriber(models.Model):
    """The base subscriber model.

    Each subscriber is identified by his e-mail address.

    Each subscriber points to a list of campaign lists he has subscribed to.
    This list is defined as a `ManyToManyField` since an individual may have
    subscribed to more than one `lists` simultaneously, while a single list
    most likely holds multiple subscribers.

    """

    lists = models.ManyToManyField(CampaignList)

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=64)
    state = models.CharField(max_length=12,
                             default='Active',
                             choices=(('Active', 'Active'),
                                      ('Bounced', 'Bounced'),
                                      ('Deleted', 'Deleted'),
                                      ('Unconfirmed', 'Unconfirmed'),
                                      ('Unsubscribed', 'Unsubscribed')))

    @property
    def active(self):
        return self.state == 'Active'

    def subscribe(self, clist):
        """Subscribe self to the specified list."""
        assert isinstance(clist, CampaignList)
        params = {'name': self.name, 'email_address': self.email}
        import_subscriber(clist.external_id, **params)
        self.lists.add(clist)

    def unsubscribe(self, clist):
        """Unsubscribe self from the specific subscribtion list."""
        assert isinstance(clist, CampaignList)
        delete_subscriber(clist.external_id, self.email)
        self.lists.remove(clist)

    def save(self, *args, **kwargs):
        """Perform full validation and save."""
        self.full_clean()
        super(CampaignSubscriber, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Delete a subscriber both locally and remotely."""
        for clist in self.lists.all():
            delete_subscriber(clist.external_id, self.email)
        super(CampaignSubscriber, self).delete(*args, **kwargs)

    def __str__(self):
        return 'Subscriber "%s"' % (self.name or self.email)


class SubscriberCreationForm(forms.ModelForm):
    """A form for adding new subscribers to an existing list."""

    lists = forms.ModelMultipleChoiceField(queryset=CampaignList.objects.all())

    class Meta:
        model = CampaignSubscriber
        fields = ('name', 'email', )
