# Author: Braedy Kuzma

from django.core.paginator import Paginator, InvalidPage
from rest_framework.views import APIView

from dash.models import Comment
from .serializers import CommentSerializer
from .verifyUtils import addCommentValidators, InvalidField, ResourceConflict, \
                         DependencyError
from .dataUtils import validateData, getCommentData, getPost
from .httpUtils import JSONResponse

class CommentView(APIView):
    """
    This view gets
    """
    def get(self, request, pid):
        # Try to pull page number out of GET
        try:
            pageNum = int(request.GET.get('page', 0))
        except ValueError:
            raise InvalidField('page', request.GET.get('page'))

        # Paginator one-indexes for some reason...
        pageNum += 1

        # Try to pull size out of GET
        try:
            size = int(request.GET.get('size', 50))
        except ValueError:
            raise InvalidField('size', request.GET.get('size'))

        # Only serve max 100 comments per page
        if size > 100:
            size = 100

        # Get comments and the count
        post = getPost(request, pid)
        comments = Comment.objects.filter(post=post)
        count = comments.count()

        # Set up the Paginator
        pager = Paginator(comments, size)

        # Get our page
        try:
            page = pager.page(pageNum)
        except InvalidPage:
            data = {'query': 'comments',
                    'count': count,
                    'comments': [],
                    'size': 0}

            if pageNum > pager.num_pages:
                # Last page is num_pages - 1 because zero indexed for external
                uri = request.build_absolute_uri('?size={}&page={}'\
                                                 .format(size,
                                                         pager.num_pages - 1))
                data['last'] = uri
            elif pageNum < 1:
                # First page is 0 because zero indexed for external
                uri = request.build_absolute_uri('?size={}&page={}'\
                                                 .format(size, 0))
                data['first'] = uri
            else:
                # Just reraise the error..
                raise

            return JSONResponse(data)

        # Start our query response
        respData = {}
        respData['query'] = 'comments'
        respData['count'] = count
        respData['size'] = size if size < len(page) else len(page)

        # Now get our data
        comSer = CommentSerializer(page, many=True)
        respData['comments'] = comSer.data

        # Build and our next/previous uris
        # Next if one-indexed pageNum isn't already the page count
        if pageNum != pager.num_pages:
            # Just use page num, we've already incremented and the external
            # inteface is zero indexed
            uri = request.build_absolute_uri('?size={}&page={}'\
                                             .format(size, pageNum))
            respData['next'] = uri

        # Previous if one-indexed pageNum isn't the first page
        if pageNum != 1:
            # Use pageNum - 2 because we're using one indexed pageNum and the
            # external interface is zero indexed
            uri = request.build_absolute_uri('?size={}&page={}'\
                                             .format(size, pageNum - 2))
            respData['previous'] = uri

        return JSONResponse(respData, status=200)

    def post(self, request, pid):
        """
        This creates comments on posts.
        """
        # Get and validate the sent data
        data = getCommentData(request)
        validateData(data, addCommentValidators)

        # See if a comment exists already
        try:
            comment = Comment.objects.get(id=data['comment']['id'])
        # We WANT it to be not found
        except Comment.DoesNotExist:
            pass
        # No error was raised which means it already exists
        else:
            raise ResourceConflict('comment', data['comment']['id'])

        # Get the post this should be attached to
        post = getPost(request, pid)

        # Ensure that the url they POST'd to was the URL they said they were
        # posting to
        if post.id != data['post']:
            data = {'post.id': post.id,
                    'query.post': data['post']}
            raise DependencyError(data)

        # Pull out comment specific data
        commentData = data['comment']

        # Build comment
        comment = Comment()
        comment.author = commentData['author']['id']
        comment.post = post
        comment.comment = commentData['comment']
        comment.contentType = commentData['contentType']
        comment.published = commentData['published']
        comment.id = commentData['id']

        comment.save()

        # TODO check if author has visibility,403 if they don't

        data = {
            "query": "addComment",
            "success": True,
            "message": "Comment Added"
        }

        return JSONResponse(data)