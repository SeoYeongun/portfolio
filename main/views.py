from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from django.views.generic.edit import  DeleteView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.contrib.auth.models import User
from django.contrib import messages
import requests
from django.db.models import Q, Count
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from portfolio import settings
from .models import Post, Comment, UserProfile, Message
from .forms import PostForm, SignUpForm, CommentForm


# Create your views here.
def base(request):
    if request.user.is_authenticated:
        unread_messages = Message.objects.filter(receiver=request.user, is_read=False)
        return render(request, 'main/base.html', {'unread_messages': unread_messages})
    return render(request, 'main/base.html')

def blog(request):
    search_query = request.GET.get('search', '')
    region_query = request.GET.get('region', '')
    category_query = request.GET.get('category', '')
    sort_query = request.GET.get('sort', 'latest')  # 기본 정렬 기준은 최신순

    # 기본 쿼리셋
    posts = Post.objects.all()

    # 검색어 필터링
    if search_query:
        posts = posts.filter(title__icontains=search_query)

    # 지역 필터링
    if region_query:
        posts = posts.filter(region=region_query)

    # 카테고리 필터링
    if category_query:
        posts = posts.filter(category__icontains=category_query)

    # 정렬
    if sort_query == 'likes':
        posts = posts.order_by('-likes')
    elif sort_query == 'comments':
        posts = posts.annotate(comment_count=Count('comments')).order_by('-comment_count')
    else:
        posts = posts.order_by('-created_at')

    regions = Post.objects.values_list('region', flat=True).distinct()
    categories = Post.objects.values_list('category', flat=True).distinct()

    return render(request, 'main/blog.html', {
        'posts': posts,
        'search_query': search_query,
        'region_query': region_query,
        'category_query': category_query,
        'sort_query': sort_query,
        'regions': regions,
        'categories': categories,
    })

def map_view(request):
    posts = Post.objects.all()
    return render(request, "main/map.html", {
        "KAKAO_MAP_KEY": settings.KAKAO_MAP_KEY,
        "posts": posts
    })

class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post
    template_name = 'main/post_detail.html'
    context_object_name = 'post'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = Comment.objects.filter(post=self.object).order_by('-created_at')
        context['comment_form'] = CommentForm()  # 댓글 작성 폼 추가
        return context

    def post(self, request, *args, **kwargs):
        post = self.get_object()
        comment_form = CommentForm(request.POST)

        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
            return redirect('post_detail', pk=post.pk)  # 댓글 작성 후 해당 게시글 페이지로 리디렉션
        return self.render_to_response({'comment_form': comment_form, 'post': post})

class ProtectedView(LoginRequiredMixin, TemplateView):
    template_name = 'main/post_new.html'
    login_url = '/login/'

class CustomLoginView(LoginView):
    template_name = 'account/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Login'
        return context

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('base')

@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            # 지역 정보가 비어있는지 확인
            region = request.POST.get('region', '').strip()
            print(f"post_create에서 받은 지역 정보: '{region}'")
            
            if not region:
                print("post_create: 지역 정보가 비어있습니다.")
                form.add_error(None, '현재 위치를 입력해주세요.')
                return render(request, 'main/post_new.html', {
                    'form': form,
                    'KAKAO_MAP_KEY': settings.KAKAO_MAP_KEY
                })
                
            post = form.save(commit=False)
            post.author = request.user
            post.region = region
            print(f"post_create: 게시물에 설정된 지역 정보: '{post.region}'")
            post.save()
            return redirect('blog')
    else:
        form = PostForm()
    
    return render(request, 'main/post_new.html', {
        'form': form,
        'KAKAO_MAP_KEY': settings.KAKAO_MAP_KEY
    })


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'main/post_delete.html'
    success_url = reverse_lazy('blog')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        print("게시물 작성자:", obj.author)  # 게시물 작성자 출력
        print("현재 로그인한 사용자:", self.request.user)  # 로그인한 사용자 출력
        if obj.author != self.request.user:
            raise PermissionDenied("삭제 권한이 없습니다.")  # 권한이 없을 경우 예외 발생
        return obj

class CommentView(LoginRequiredMixin, TemplateView):
    model = Comment
    form_class = CommentForm
    context_object_name = 'comments'
    template_name = 'main/post_detail.html'

@login_required
@require_POST
def post_like(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user in post.likes.all():
        post.likes.remove(request.user)  # 좋아요 취소
    else:
        post.likes.add(request.user)  # 좋아요 추가
    return redirect('post_detail', pk=pk)

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 사용자 프로필 생성
            profile = UserProfile.objects.create(user=user)
            
            # 현재 위치 정보가 있으면 저장
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            address = request.POST.get('address')
            
            if latitude and longitude:
                profile.latitude = latitude
                profile.longitude = longitude
                profile.address = address
                
                # 주소에서 지역 정보 추출 (예: "서울시 강남구" -> "강남구")
                if address:
                    parts = address.split()
                    if len(parts) > 1:
                        profile.region = parts[1]
                
                profile.save()
            
            messages.success(request, '회원가입이 완료되었습니다. 로그인해주세요.')
            return redirect('login')
    else:
        form = UserCreationForm()
    
    return render(request, 'account/signup.html', {
        'form': form,
        'KAKAO_MAP_KEY': settings.KAKAO_MAP_KEY
    })



@require_POST
def comment_delete(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user == comment.author:
        comment.delete()
        messages.success(request, '댓글이 삭제되었습니다.')
    else:
        messages.error(request, '댓글을 삭제할 권한이 없습니다.')
    return redirect('post_detail', pk=comment.post.pk)

@require_POST
def comment_edit(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user == comment.author:
        content = request.POST.get('content')
        if content:
            comment.content = content
            comment.save()
            messages.success(request, '댓글이 수정되었습니다.')
        else:
            messages.error(request, '댓글 내용을 입력해주세요.')
    else:
        messages.error(request, '댓글을 수정할 권한이 없습니다.')
    return redirect('post_detail', pk=comment.post.pk)

def user_profile(request, username):
    user = get_object_or_404(User, username=username)
    user_profile = UserProfile.objects.get_or_create(user=user)[0]
    
    # 사용자가 작성한 게시글
    user_posts = Post.objects.filter(author=user).order_by('-date_posted')
    
    # 사용자가 좋아요한 게시글
    liked_posts = Post.objects.filter(likes=user).order_by('-date_posted')
    
    # 사용자가 댓글을 단 게시글
    commented_posts = Post.objects.filter(comments__author=user).distinct().order_by('-date_posted')
    
    # 탭 선택 (기본값: 작성한 게시글)
    active_tab = request.GET.get('tab', 'posts')
    
    context = {
        'profile_user': user,
        'user_profile': user_profile,
        'user_posts': user_posts,
        'liked_posts': liked_posts,
        'commented_posts': commented_posts,
        'active_tab': active_tab
    }
    
    return render(request, 'main/user_profile.html', context)

@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user == post.author:
        if request.method == 'POST':
            post.delete()
            messages.success(request, '게시글이 삭제되었습니다.')
            return redirect('blog')
        return render(request, 'main/post_confirm_delete.html', {'post': post})
    else:
        messages.error(request, '게시글을 삭제할 권한이 없습니다.')
        return redirect('post_detail', pk=pk)

def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    comments = post.comments.all().order_by('-created_at')
    comment_form = CommentForm()
    
    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect('post_detail', pk=pk)
    
    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form
    }
    return render(request, 'main/post_detail.html', context)
    

@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user != post.author:
        messages.error(request, '게시글을 수정할 권한이 없습니다.')
        return redirect('post_detail', pk=pk)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, '게시글이 수정되었습니다.')
            return redirect('post_detail', pk=pk)
    else:
        form = PostForm(instance=post)
    
    return render(request, 'main/post_edit.html', {
        'form': form,
        'post': post
    })

@login_required
def comment_create(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Comment.objects.create(
                post=post,
                author=request.user,
                content=content
            )
    return redirect('post_detail', pk=pk)

@login_required
def comment_like(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.user in comment.dislikes.all():
        comment.dislikes.remove(request.user)  # 비추천 취소
    if request.user in comment.likes.all():
        comment.likes.remove(request.user)  # 추천 취소
    else:
        comment.likes.add(request.user)  # 추천 추가
    return redirect('post_detail', pk=comment.post.pk)

@login_required
def comment_dislike(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.user in comment.likes.all():
        comment.likes.remove(request.user)  # 추천 취소
    if request.user in comment.dislikes.all():
        comment.dislikes.remove(request.user)  # 비추천 취소
    else:
        comment.dislikes.add(request.user)  # 비추천 추가
    return redirect('post_detail', pk=comment.post.pk)

@login_required
def post_new(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            region = request.POST.get('region', '').strip()
            if not region:
                form.add_error(None, '지역 정보를 입력해주세요.')
                return render(request, 'main/post_new.html', {
                    'form': form,
                    'KAKAO_MAP_KEY': settings.KAKAO_MAP_KEY
                })
            
            post = form.save(commit=False)
            post.author = request.user
            post.region = region
            post.save()
            return redirect('blog')
    else:
        form = PostForm()
    
    return render(request, 'main/post_new.html', {
        'form': form,
        'KAKAO_MAP_KEY': settings.KAKAO_MAP_KEY
    })

def get_address_from_coords(request):
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    
    if not lat or not lon:
        return JsonResponse({'error': 'Invalid coordinates'}, status=400)
    
    # 카카오 맵 API를 사용하여 좌표를 주소로 변환
    kakao_api_key = settings.KAKAO_MAP_KEY  # 실제 카카오 API 키로 대체
    url = f"https://dapi.kakao.com/v2/local/geo/coord2address.json?x={lon}&y={lat}"
    headers = {"Authorization": f"KakaoAK {kakao_api_key}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data['documents']:
            address = data['documents'][0]['address']['address_name']
            return JsonResponse({'address': address})
        else:
            return JsonResponse({'error': 'No address found'}, status=404)
    else:
        return JsonResponse({'error': 'Failed to fetch address'}, status=response.status_code)
    
@login_required
def chat_view(request, room_name):
    messages = Message.objects.filter(room_name=room_name)
    return render(request, 'main/chat.html', {
        'room_name': room_name,
        'messages': messages
    })

@login_required
def lobby_view(request):
    return render(request, 'main/lobby.html')


