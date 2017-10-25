from django.contrib import admin

from .models import CampaignList
from .models import CampaignSubscriber
from .models import SubscriberCreationForm


class CampaignListInline(admin.TabularInline):

    model = CampaignSubscriber.lists.through

    extra = 1
    verbose_name_plural = "Subscription Lists"

    def has_add_permission(self, request, obj=None):
        return True if obj is not None else False


class CampaignSubscriberInline(admin.TabularInline):

    model = CampaignSubscriber.lists.through

    extra = 1
    verbose_name_plural = "Subscribers List"


class CampaignListAdmin(admin.ModelAdmin):

    inlines = (CampaignSubscriberInline, )

    actions = ('purge', 'delete_selected', )

    list_display = ('name', 'active', 'subscribers', )

    readonly_fields = ('name', 'client', 'external_id', )

    def subscribers(self, clist):
        return clist.campaignsubscriber_set.count()

    def active(self, clist):
        return clist.campaignsubscriber_set.filter(state='Active').count()

    def purge(self, request, queryset):
        for clist in queryset:
            for sub in clist.campaignsubscriber_set.all():
                sub.delete()
    purge.short_description = 'Delete subscribers (only)'

    def delete_selected(self, request, queryset):
        for clist in queryset:
            clist.delete()
    delete_selected.short_description = 'Delete lists'

    def save_related(self, request, form, formsets, change):
        old_subs = set(form.instance.campaignsubscriber_set.all())
        super(CampaignListAdmin, self).save_related(request, form, formsets,
                                                    change)
        new_subs = set(form.instance.campaignsubscriber_set.all())
        # Calculate the diff of subscribers prior to and after the update
        # operation (using a logical XOR) in order to update the upstream
        # subscription list.
        for sub in (old_subs ^ new_subs):
            if sub in new_subs:
                form.instance.subscribe(sub)
            if sub in old_subs:
                form.instance.unsubscribe(sub)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CampaignSubscriberAdmin(admin.ModelAdmin):

    form = SubscriberCreationForm

    inlines = (CampaignListInline, )
    exclude = ("lists", )

    actions = ("delete_selected", )

    fieldsets = (
        ("SUBSCRIBER DETAILS", {
            "fields": ("name", "email", "state", )
        }),
        ("SUBSCRIBER'S LISTS", {
            "fields": ("lists", )
        }),

    )

    search_fields = ('name', 'email', )
    list_display = ('name', 'email', 'state', )
    list_display_links = ('email', )

    def save_related(self, request, form, formsets, change):
        old_lists = set(form.instance.lists.all())
        super(CampaignSubscriberAdmin, self).save_related(request, form,
                                                          formsets, change)
        new_lists = set(form.instance.lists.all())
        for clist in (old_lists ^ new_lists):
            if clist in new_lists:
                clist.subscribe(form.instance)
            if clist in old_lists:
                clist.unsubscribe(form.instance)

    def delete_selected(self, request, queryset):
        for subscriber in queryset:
            subscriber.delete()
    delete_selected.short_description = 'Delete'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = ('state', )
        if obj is not None:
            readonly_fields += ('name', 'email', 'lists', )
        return readonly_fields


admin.site.register(CampaignList, CampaignListAdmin)
admin.site.register(CampaignSubscriber, CampaignSubscriberAdmin)
