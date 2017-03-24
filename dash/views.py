# Author: Braedy Kuzma

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.views import generic
from .models import Post, Category, Comment, CanSee, Author
from django.db.models import Q
from .forms import PostForm, CommentForm
from .serializers import AuthorSerializer
import base64
import uuid
import itertools
from django.views.generic.edit import CreateView

class StreamView(LoginRequiredMixin, generic.ListView):
    login_url = 'login'
    template_name = 'dashboard.html'
    context_object_name = 'latest_post_list'
    def get_queryset(self):
        # Return posts that are visible to everyone (Public, this server only,
        # self posted. Remove unlisted unless you are the creator of post)

        localVisible = Post.objects.filter(
            ((Q(visibility='PUBLIC') | Q(visibility='SERVERONLY'))\
             & Q(unlisted=False)) | Q(author=self.request.user.author)
        )

        # Get authors who consider this author a friend
        #friendOf = AuthorFriend.objects \
         #                      .filter(friendId=self.request.user.author.id) \
          #                     .values_list('friend1', flat=True)
        #friends=Author.objects.filter(followee__follower__user__username=self.request.user.username,followee__bidirectional=True)
        # Get posts marked FRIENDS visibility whose authors consider this author
        # a friend

        # friendsPosts = Post.objects\
        #                    .filter(visibility='FRIENDS', author__in=friends,
        #                             unlisted=False)
        #friendsPosts=Post.objects\
         #                   .filter(visibility='FRIENDS')\
          #                  .filter(author__followee__follower__user__username=self.request.user.username,author__followee__bidirectional=True)

        # Get posts you can see
        authorCanSee = CanSee.objects\
                             .filter(visibleTo=self.request.user.author.url) \
                             .values_list('post', flat=True)
        visibleToPosts = Post.objects \
                             .filter(id__in=authorCanSee, visibility="PRIVATE",
                                        unlisted=False)

        #finalQuery = itertools.chain(localVisible, friendsPosts, visibleToPosts)
        finalQuery = itertools.chain(localVisible, visibleToPosts)
        return sorted(finalQuery, key=lambda post: post.published, reverse=True)

    def get_context_data(self, **kwargs):
        context = generic.ListView.get_context_data(self, **kwargs)
        context['postForm'] = PostForm()
        context['commentForm'] = CommentForm()
        return context

@require_POST
@login_required(login_url="login")
def newPost(request):
    # Get form data
    form = PostForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data

        host = 'http://' + request.get_host()
        # Did they upload an image?
        if 'attachImage' in request.FILES:
            # Build a bytes object from all of the image chunks (theoretically
            # only) one, but you never know
            image = request.FILES['attachImage']
            b = bytes()
            for c in image.chunks():
                b += c

            # Encode it in b64
            encoded = base64.b64encode(b)

            # Make the new post
            iPost = Post()
            imageId = uuid.uuid4().hex
            iPost.id = host + '/posts/' + imageId + '/'
            iPost.author = request.user.author

            # These are empty because they're just an extra post
            iPost.title = ''
            iPost.description = ''

            # Set up image content
            iPost.contentType = image.content_type + '; base64'
            iPost.content = encoded

            # Image posts are PRIVATE
            iPost.visibility = 'PRIVATE'

            # Image posts are unlisted
            iPost.unlisted = True

            # Save the image post
            iPost.save()

        # Make new post
        post = Post()

        # Fill in data
        post.id = host + '/posts/' + uuid.uuid4().hex + '/'
        post.author = request.user.author
        post.title = data['title']
        post.contentType = data['contentType']
        post.content = data['content']
        post.visibility = data['visibility']
        post.unlisted = data['unlisted']
        post.description = data['description']

        if 'attachImage' in request.FILES:
            post.content += '\n\n![' + post.title + '](' + host + '/dash/posts/' + imageId + ' "' + post.title + '")'

        # Save the new post
        post.save()

        # Were there any categories?
        if data['categories']:
            # Normalize the categories
            categoryList = data['categories'].split(',')
            categoryList = [i.strip() for i in categoryList]

            # Build Category objects
            for categoryStr in categoryList:
                category = Category()
                category.category = categoryStr
                category.post = post
                category.save()

        if data['visibleTo']:
            visibilityList = data['visibleTo'].split(',')
            visibilityList = [i.strip() for i in visibilityList]

            # Build Category objects
            for author in visibilityList:
                canSee = CanSee()
                canSee.visibleTo = author
                canSee.post = post
                canSee.save()

    # Redirect to the dash
    return redirect('dash:dash')


@require_POST
@login_required(login_url="login")
def newComment(request):
    # Get form data
    data = request.POST

    # Make new comment
    comment = Comment()

    # Fill in data
    comment.author = request.user.author.id
    comment.comment = data['comment']
    comment.contentType = data['contentType']
    comment.post_id = data['post_id']

    # Save the new comment
    comment.save()

    # Redirect to the dash
    return redirect('dash:dash')


@require_POST
@login_required(login_url="login")
def friendRequest(request):
    # Get form data
    data = request.POST
    print(data)

    # Redirect to the dash
    return redirect('dash:dash')


class ManagerView(LoginRequiredMixin, generic.ListView):
    login_url = 'login'
    template_name = 'manager.html'
    context_object_name = 'latest_post_list'
    def get_queryset(self):
        # Return posts that are visible to everyone (Public, this server only,
        # self posted)
        localVisible = Post.objects.filter(
            Q(author=self.request.user.author)
        )

        return sorted(localVisible, key=lambda post: post.published, reverse=True)

    def get_context_data(self, **kwargs):
        context = generic.ListView.get_context_data(self, **kwargs)
        context['postForm'] = PostForm()
        context['commentForm'] = CommentForm()
        return context

@require_POST
@login_required(login_url="login/")
def editPost(request):
    # Get form data
    form = PostForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data

        host = 'http://' + request.get_host()
        # Did they upload an image?
        if 'attachImage' in request.FILES:
            # Build a bytes object from all of the image chunks (theoretically
            # only) one, but you never know
            image = request.FILES['attachImage']
            b = bytes()
            for c in image.chunks():
                b += c

            # Encode it in b64
            encoded = base64.b64encode(b)

            # Make the new post
            iPost = Post()
            imageId = uuid.uuid4().hex
            iPost.id = host + '/posts/' + imageId
            iPost.author = request.user.author

            # These are empty because they're just an extra post
            iPost.title = ''
            iPost.description = ''

            # Set up image content
            iPost.contentType = image.content_type + '; base64'
            iPost.content = encoded

            # Image posts are PRIVATE
            iPost.visibility = 'PRIVATE'

            # Image posts are unlisted
            iPost.unlisted = True

            # Save the image post
            iPost.save()

        # Make new post
        post = Post.objects.get(pk=data['post_id'])

        # Fill in data
        post.title = data['title']
        post.contentType = data['contentType']
        post.content = data['content']
        post.visibility = data['visibility']
        post.unlisted = data['unlisted']
        post.description = data['description']

        if 'attachImage' in request.FILES:
            post.content += '\n\n![' + post.title + '](' + host + '/dash/posts/' + imageId + ' "' + post.title + '")'

        # Save the new post
        post.save()

        # Were there any categories?
        if data['categories']:
            # Normalize the categories
            categoryList = data['categories'].split(',')
            categoryList = [i.strip() for i in categoryList]

            # Build Category objects
            for categoryStr in categoryList:
                category = Category()
                category.category = categoryStr
                category.post = post
                category.save()

    # Redirect to the dash
    return redirect('dash:dash')

@login_required(login_url="login")
def post(request, pid):
    pid = 'http://' + request.get_host() + '/posts/' + pid
    post = get_object_or_404(Post, pk=pid)
    if 'base64' in post.contentType:
        return HttpResponse(base64.b64decode(post.content), content_type=post.contentType)
    return render(request, 'post.html', {'post':post})


def author_handler(request, id):
    #Return the foreign author's profile
    if (request.method == 'POST'):
        return HttpResponse(status=405)

    elif (request.method == 'GET'):
        author = Author.objects.get(id=id)
        author.friends = author.friends.all()
        author.url = author.host + 'author/' + str(author.id)
        serializer = AuthorSerializer(author)
        json_data = JSONRenderer().render(serializer.data)

        return HttpResponse(json_data, content_type='application/json')

#class FollowForm(LoginRequiredMixin,CreateView):
 #   ''' Form for sending friend (follow) requests'''
    #model = Follow
    #fields = ['followee']
  #  template_name = 'followform.html'
  #  success_url = '/dash/following'

   # ''' This part of code is for making sure you cant follow yourself and you can't send duplicate follow requests '''
   # def form_valid(self,form):
    #    print(Follow.objects.filter(follower=self.request.user.author,followee=form.instance.followee))
     #   if Follow.objects.filter(follower=self.request.user.author,followee=form.instance.followee).count()>0:
      #      print("Already Followed! Try some other user!")
       #     form.add_error('followee', "Already Followed! Try some other user!")
        #    return self.form_invalid(form)
       # elif form.instance.followee==self.request.user.author:
        #    print("cant follow yourself")
         #   form.add_error('followee', "Can't Follow yourself")
          #  return self.form_invalid(form)
        #else:
         #   print("form valid",Follow.objects.filter(follower=self.request.user.author,followee=form.instance.followee).count())
          #  form.instance.follower = self.request.user.author
           # return super(FollowForm, self).form_valid(form)
class ListFollowsAndFriends(LoginRequiredMixin, generic.ListView):
    ''' Lists whom you are following, who are following you and who are your friends '''

    context_object_name = 'following'
    template_name = 'following.html'

    def get_queryset(self):
        notFriends = Follow.objects.filter(follower=self.request.user.author,bidirectional=False)
        Friends = Follow.objects.filter(follower=self.request.user.author,bidirectional=True)
        FollowingMe = Follow.objects.filter(followee=self.request.user.author,bidirectional=False)
        print(FollowingMe)
        return {'notFriends':notFriends,'Friends':Friends,'FollowingMe':FollowingMe}

@login_required()
def FollowRequests(request):
    ''' Accept or reject Friend requests '''
    friend_requests = Follow.objects.filter(followee=request.user.author,bidirectional=False,reject=False)
    if request.method == 'POST':
        if 'accept' in request.POST:
            follower = request.POST['accept']
            print(follower)
            obj = Follow.objects.get(follower=Author.objects.get(user__username=follower),followee=request.user.author)
            obj.bidirectional=True
            obj.save()
            obj = Follow(followee=Author.objects.get(user__username=follower),follower=request.user.author)
            obj.bidirectional=True
            obj.save()
        elif 'reject' in request.POST:
            follower = request.POST['reject']
            obj = Follow.objects.get(follower=Author.objects.get(user__username=follower),followee=request.user.author)
            obj.reject = True
            obj.save()

    return render(request, 'friendrequests.html', {'followers': friend_requests})
