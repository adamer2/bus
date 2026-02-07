from django.db import models


class BUser(models.Model):
    class Menu(models.IntegerChoices):
        pass

    class Status(models.TextChoices):
        pass

    class Rank(models.TextChoices):
        pass

    class MenuMode(models.TextChoices):
        pass

    chat_id = models.BigIntegerField(unique=True)
    status = models.CharField(max_length=1, choices=Status)
    rank = models.CharField(max_length=1, choices=Rank)
    menu_mode = models.CharField(max_length=1, choices=MenuMode)
    menu = models.PositiveSmallIntegerField(choices=Menu)
    back_menu = models.CharField(max_length=50, null=True, blank=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    last_usage_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ('id',)

    def __str__(self):
        return f'{self.chat_id}:{self.get_rank_display()}'
