import logging

from .models import CampaignList
from .models import CampaignClient
from .models import CampaignSubscriber
from .models import SubscriberCreationForm

from .upstream import sync_client
from .upstream import import_subscriber
from .upstream import delete_subscriber

from django.urls import reverse
from django.http import Http404
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404

from django.views.generic import DetailView
from django.views.generic import DeleteView
from django.views.generic.edit import CreateView


log = logging.getLogger(__name__)


class CampaignClientDetail(DetailView):
    """Return details of a single client, including lists and subscribers."""

    model = CampaignClient
    pk_url_kwarg = None  # Prevent a pk lookup.

    slug_field = 'external_id'  # The db field to be used in the client query.
    slug_url_kwarg = 'client_id'  # The URL param that holds the client id.

    def get(self, request, *args, **kwargs):
        """Retrieve the information of a campaign client.

        If the client with the specified ClientID does not exist, then the
        client's data is fetched and also stored locally.

        This endpoint basically serves as a cachable proxy between the local
        app and Campaign Monitor's API.

        """
        try:
            self.object = self.get_object()
        except Http404 as err:
            log.warning('Pulling new client (%s) details', kwargs['client_id'])
            try:
                self.object = sync_client(kwargs['client_id'])
            except Exception as exc:
                log.error('Failed to sync client details: %r', exc)
                raise err
        return super(CampaignClientDetail, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Enrich context with the corresponding client and campaign lists."""
        context = super(CampaignClientDetail, self).get_context_data(**kwargs)
        context['client'] = self.object
        context['lists'] = self.object.campaignlist_set.all()
        return context


class AddSubscriberToList(CreateView):
    """Import a new subscriber to an existing subscription list."""

    # Declare model and form classes.
    model = CampaignSubscriber
    form_class = SubscriberCreationForm

    # The template to render.
    template_name = 'app/add_subscriber_form.html'

    # Allowed HTTP methods.
    http_method_names = ['get', 'post']

    def post(self, request, *args, **kwargs):
        """Process subscriber data and redirect to `success_url`.

        Attempt to add a new (active) subscriber to an existing campaign
        list. If the subscriber (e-mail address) already exists as part
        of the specified subscription list, then their information will
        be updated.

        """
        # Prepare intial request params.
        name = self.request.POST.get('name')
        email = self.request.POST.get('email')
        params = {'name': name, 'email_address': email}

        for clist_id in request.POST.getlist('lists'):

            # Get subscription list and verify ownership.
            self.clist = get_object_or_404(CampaignList, pk=clist_id)
            if self.clist.client.external_id != kwargs['client_id']:
                raise Http404

            # Attempt to add new subscriber to the specified list.
            try:
                params.update({'list_id': self.clist.external_id})
                import_subscriber(**params)
            except Exception as exc:
                log.error('Failed to import subscriber: %r', exc)
                raise

            # Persist locally. The object is instantiated either by fetching it
            # from the db or while processing the corresponding form during the
            # call to `super()` in case we are creating a new object.
            try:
                self.object = CampaignSubscriber.objects.get(email=email)
                self.object.name = name
            except CampaignSubscriber.DoesNotExist:
                http_redirect = super(
                    AddSubscriberToList,self).post(request, *args, **kwargs)
            else:
                http_redirect = HttpResponseRedirect(self.get_success_url())
            self.object.lists.add(self.clist)
            self.object.save()

        return http_redirect

    def get_success_url(self):
        """Redirect to the client's detailed view upon success."""
        return reverse(
            'client', kwargs={'client_id': self.clist.client.external_id}
        )


class RemoveSubscriberFromList(DeleteView):
    """Remove an existing subscriber from a list."""

    model = CampaignSubscriber
    pk_url_kwarg = 'subscriber_id'

    def post(self, request, *args, **kwargs):
        """Delete the requested object.

        Fetches the subscriber instance from db and verifies the chain of
        ownership all the way to the campaign client. This also serves as
        a naive substitute for authentication.

        This view works with a POST request method, which is mapped internally
        to DELETE.

        """
        subscriber = self.get_object()
        for clist in subscriber.lists.all():
            if clist.external_id != kwargs['list_id']:
                continue
            if clist.client.external_id != kwargs['client_id']:
                continue
            self.clist= clist
            break
        else:
            raise Http404()
        try:
            delete_subscriber(clist.external_id, subscriber.email)
        except Exception as exc:
            log.error('Failed to remove subscriber: %r', exc)
            raise
        return super(RemoveSubscriberFromList, self).post(request,
                                                          *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """Delete the fetched object and then redirect to the success URL.

        Initially takes care of disassociating subscribers from mailing lists.
        If a subscriber does not belong to any list, then the delete() method
        is also called on the db object.

        """
        self.object = self.get_object()
        self.object.lists.remove(self.clist)
        if not self.object.lists.count():
            self.object.delete()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            'client', kwargs={'client_id': self.clist.client.external_id}
        )
