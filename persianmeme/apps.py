from django.apps import AppConfig


class PersianmemeConfig(AppConfig):
    name = 'persianmeme'

    def ready(self):
        from . import signals
