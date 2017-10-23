from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^(?P<client_id>[a-zA-z0-9]+)/$',
        views.CampaignClientDetail.as_view(), name='client'),
    url(r'^(?P<client_id>[a-zA-Z0-9]+)/lists/subscribe/$',
        views.AddSubscriberToList.as_view(), name='add-subscriber'),
    url(r'^(?P<client_id>[a-zA-z0-9]+)/lists/(?P<list_id>[a-zA-z0-9]+)/subscribers/(?P<subscriber_id>[a-zA-z0-9]+)/unsubscribe/$',
        views.RemoveSubscriberFromList.as_view(), name='remove-subscriber'),
]
