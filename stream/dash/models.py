from django.db import models
from django.conf import settings
import django.utils.timezone as timezone
import uuid

class Post(models.Model):
    title = models.CharField(max_length=32)
    source = models.CharField(max_length=128)
    origin = models.CharField(max_length=128)
    description = models.CharField(max_length=140) # why not Twitter?
    contentType = models.CharField(max_length=32)
    content = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                               null=True, # Lets the key be null
                               on_delete=models.SET_NULL, # TODO is this what we want
                               related_name='author')
    categories = models.CharField(max_length=128)
    count = models.PositiveIntegerField(default=0)
    size = models.PositiveIntegerField(default=0)
    nextComments = models.CharField('next', max_length=128)
    published = models.DateTimeField(default=timezone.now)

    # This should really have a validator
    uuid = models.CharField('id', max_length=36, default=uuid.uuid4)
    visibility = models.CharField(max_length=10, default="PUBLIC")
    visibleTo = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                       related_name='visibleTo')
    unlisted = models.BooleanField(default=False)