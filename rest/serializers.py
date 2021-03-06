# Author: Braedy Kuzma

from urllib.parse import urlsplit, urlunsplit

from django.core.paginator import Paginator
from rest_framework import serializers
import requests

from dash.models import Post, Author, Comment, Category, CanSee, \
                        RemoteCommentAuthor
from .models import RemoteCredentials
from .authUtils import getRemoteCredentials

class FollowSerializer(serializers.BaseSerializer):
    def to_representation(self, follow):
        data = {}
        try:
            author = Author.objects.get(id=follow.friend)
            data['id'] = author.id
            data['host'] = author.host
            data['displayName'] = author.user.get_username()
            data['url'] = author.id
        except Author.DoesNotExist:
            # Build the fallback host
            split = urlsplit(follow.friend)
            split = (split.scheme, split.netloc, '', '', '')
            url = urlunsplit(split) + '/'

            # Set everything up with values, if we can successfully get a user
            # from remote then we'll update
            followId = follow.friend
            data['id'] = followId
            data['host'] = url
            data['displayName'] = 'UnkownRemoteUser'
            data['url'] = followId

            remoteCreds = getRemoteCredentials(followId)
            if remoteCreds != None:
                req = requests.get(followId, auth=(remoteCreds.username,
                                                   remoteCreds.password))
                if req.status_code == 200:
                   try:
                       # Try to parse JSON out
                       reqData = req.json()

                       # We could just pass along everything, but the spec
                       # says pick and choose these
                       data['id'] = reqData['id']
                       data['host'] = reqData['host']
                       data['displayName'] = reqData['displayName']
                       data['url'] = reqData['url']
                   # Couldn't parse json, just give up
                   except ValueError:
                       print('Could not parse JSON from author follow request')
                else:
                    print(('Got status code {} while requesting follow user. ' \
                           'Using "{}" for {}.') \
                          .format(req.status_code, remoteCreds, followId))
                    print('TEXT\n', req.text)
            else:
                print('Could not get remote credentials for follow id: {}' \
                      .format(followId))

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ('id', 'host', 'url', 'github')

    def to_representation(self, author):
        rv = serializers.ModelSerializer.to_representation(self, author)
        rv['displayName'] = author.user.get_username()

        # Did the caller want the friends added?
        if self.context.get('addFriends', False):
            # Right now, we're calling all of our follows our friends,
            # if this needs to be actually VERIFIED friends it's going to be
            # a lot more costly..
            folSer = FollowSerializer(author.follow.all(), many=True)
            rv['friends'] = folSer.data

        return rv

class AuthorFromIdSerializer(serializers.BaseSerializer):
    def to_representation(self, authorId):
        data = {}
        print('AUTHOR FROM ID REP', authorId)
        try:
            author = Author.objects.get(id=authorId)
            data['id'] = author.id
            data['host'] = author.host
            data['displayName'] = author.user.get_username()
            data['url'] = author.url
            data['github'] = author.github
        # No sweat, they could be remote user
        except Author.DoesNotExist:
            try:
                author = RemoteCommentAuthor.objects.get(authorId=authorId)
                data['id'] = author.authorId
                data['host'] = author.host
                data['displayName'] = author.displayName
                data['url'] = author.authorId
                data['github'] = author.github
            # We couldn't find a remote author either?!
            except RemoteCommentAuthor.DoesNotExist:
                # Print some reasonable debug and blow up
                print('Could not get remote credentials for author id: {}' \
                      .format(authorId))
                raise

        return data

class CategorySerializer(serializers.BaseSerializer):
    def to_representation(self, category):
        return category.category

class CanSeeSerializer(serializers.BaseSerializer):
    def to_representation(self, canSee):
        return canSee.visibleTo

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = '__all__'
    author = AuthorSerializer()

    def to_representation(self, post):
        rv = serializers.ModelSerializer.to_representation(self, post)
        categories = Category.objects.filter(post=post)
        catSer = CategorySerializer(categories, many=True)
        rv['categories'] = catSer.data

        # The source and the origin is the same as the id -- so says the Hindle
        rv['source'] = rv['id']
        rv['origin'] = rv['id']

        # Get comments and add count to rv
        comments = Comment.objects.filter(post=post)
        count = comments.count()
        rv['count'] = count

        # Get number of comments to attach and add to rv
        pageSize = self.context.get('commentPageSize', 50)
        rv['size'] = pageSize if count > pageSize else count

        # Serialize and attach the first page
        pager = Paginator(comments, pageSize)
        commSer = CommentSerializer(pager.page(1), many=True)
        rv['comments'] = commSer.data

        # Serialize and attach list of visibileTo
        canSees = CanSee.objects.filter(post=post)
        canSer = CanSeeSerializer(canSees, many=True)
        rv['visibleTo'] = canSer.data

        return rv

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('author', 'comment', 'contentType', 'published', 'id')

    author = AuthorFromIdSerializer()
