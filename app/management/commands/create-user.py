from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    help = 'Create a new user [non-interactively]'

    def add_arguments(self, parser):
        parser.add_argument('-u', '--username', default='admin')
        parser.add_argument('-p', '--password', default='admin')
        parser.add_argument('-e', '--email', default='admin@example.com')
        parser.add_argument('-s', '--super', default=True, action='store_true')

    def handle(self, *args, **options):
        email = options['email']
        username = options['username']
        password = options['password']
        superuser = options['super']
        try:
            model = get_user_model()
            model.objects.get(username=username)
            self.stdout.write('User %s already exists' % username)
        except model.DoesNotExist:
            self.stdout.write('Creating user %s:%s (%s)' % (username,
                                                            password, email))
            if superuser:
                model.objects.create_superuser(username, email, password)
            else:
                model.objects.create_user(username, email, password)
