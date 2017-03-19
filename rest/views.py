# Author: Braedy Kuzma

import uuid
import json
from datetime import datetime

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
import django.utils.timezone as timezone
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

from dash.models import Post, Comment, Author, Category, CanSee
from .serializers import PostSerializer
from .utils import InvalidField, NotFound, MalformedBody, MalformedId, \
                   ResourceConflict, MissingFields
from .utils import postValidators

# Initially taken from
# http://www.django-rest-framework.org/tutorial/1-serialization/
class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json; charset=utf-8'
        super(JSONResponse, self).__init__(content, **kwargs)

def validateData(data, fields):
    """
    Validates data in a dictionary using validation functions.

    Validation functions return a updated, validated version of their value.
    Validation functions should raise InvalidField exceptions when they fail to
    validate their data.
    """
    for key, validator in fields:
        if key in data:
            data[key] = validator(key, data[key])

def requireFields(data, required):
    """
    Ensure that data has required fields. No return on success.

    Raises MissingFields if fields are missing from data.
    """
    # Make sure we have required fields
    notFound = []
    for key in required:
        if key not in data:
            notFound.append(key)

    # If we didn't find required keys return an error
    if notFound:
        raise MissingFields(notFound)

def pidToUrl(request, pid):
    """
    Change a URL pid to a locally valid post id URL.

    Returns a url string on success or an appropriate HttpResponse on failure.
    """
    try:
        urlUuid = uuid.UUID(pid)
        url = 'http://' + request.get_host() + '/posts/' + urlUuid.hex + '/'
    except ValueError:
        # Include the bad ID in the response
        raise MalformedId('post', request.build_absolute_uri(request.path))

    return url

def getPost(request, pid):
    """
    Get a post by pid in URL.

    pid = Post id (uuid4, any valid format available from uuid python lib)

    Returns a post object on success or an appropriate HttpResponse on failure.
    """
    # Get url or error response
    url = pidToUrl(request, pid)
    try:
        post = Post.objects.get(id=url)
    # Url was valid but post didn't exist
    except Post.DoesNotExist:
        # Include the bad ID in the response
        raise NotFound('post', request.build_absolute_uri(request.path))

    return post

def getPostData(request):
    """
    Returns post data from POST request.
    Raises MalformedBody if post body was malformed.
    """
    # Ensure that the body of the request is valid
    try:
        data = json.loads(str(request.body, encoding='utf-8'))
    except json.decoder.JSONDecodeError:
        raise MalformedBody(request.body)

    # Ensure required fields are present
    required = ('author', 'title', 'content', 'contentType', 'visibility')
    requireFields(data, required)

    return data

class PostView(APIView):
    """
    REST view of an individual Post.
    """
    def delete(self, request, pid=None):
        """
        Deletes a post.
        """
        # Get the post
        post = getPost(request, pid)

        # Save the id for the return
        postId = post.id

        # Delete the post
        post.delete()

        # Return
        data = {'deleted': postId}
        return JSONResponse(data)

    def get(self, request, pid=None):
        """
        Gets a post.
        """
        # Get post
        post = getPost(request, pid)

        # Serialize post
        postSer = PostSerializer(post)
        postData = postSer.data

        # TODO: Add query?
        # postData['query'] = 'post'

        return JSONResponse(postData)

    def post(self, request, pid=None):
        """
        Creates a post.
        """
        try:
            # This has the potential to raise NotFound AND MalformedId
            # If it's MalformedId we want it to fail
            post = getPost(request, pid)
        # We WANT it to be not found
        except NotFound:
            pass
        # No error was raised which means it already exists
        else:
            raise ResourceConflict('post',
                                   request.build_absolute_uri(request.path))

        # Get and validate data
        data = getPostData(request)
        validateData(data, postValidators)

        # Get id url
        url = pidToUrl(request, pid)

        # Fill in required fields
        post = Post()
        post.id = url
        post.title = data['title']
        post.contentType = data['contentType']
        post.content = data['content']
        post.author = Author.objects.get(id=data['author'])
        post.visibility = data['visibility']

        # Fill in unrequired fields
        post.unlisted = data.get('unlisted', False)
        post.description = data.get('description', '')
        post.published = data.get('published', timezone.now())

        # Save
        post.save()

        # Were there any categories?
        if 'categories' in data and data['categories']:
            categoryList = data['categories']

            # Build Category objects
            for categoryStr in categoryList:
                category = Category()
                category.category = categoryStr
                category.post = post
                category.save()

        if 'visibleTo' in data and data['visibleTo']:
            visibleToList = data['visibleTo']
            print(visibleToList)
            # Build can see list
            for authorId in visibleToList:
                canSee = CanSee()
                canSee.post = post
                canSee.visibleTo = authorId
                canSee.save()

        # Return
        data = {'created': post.id}
        return JSONResponse(data)
