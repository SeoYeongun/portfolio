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
from django.conf import settings
from tmdbv3api import TMDb, Movie, Discover
from .models import Post, Comment, UserProfile, Message, Movie as MovieModel
from .forms import PostForm, SignUpForm, CommentForm
from datetime import datetime

# TMDB 설정
tmdb = TMDb()
tmdb.api_key = settings.TMDB_API_KEY
tmdb.language = 'ko'

# Create your views here.
def base(request):
    if request.user.is_authenticated:
        unread_messages = Message.objects.filter(receiver=request.user, is_read=False)
    query = request.GET.get('q', '')
    if query:
        tmdb = TMDb()
        tmdb.api_key = settings.TMDB_API_KEY
        tmdb.language = 'ko'
        
        movie = Movie()
        search_results = movie.search(query)
        
        # 검색 결과에서 영화 정보 추출
        movies = []
        for result in search_results:
            try:
                movie_info = {
                    'id': result.id,
                    'title': result.title,
                    'overview': result.overview,
                    'release_date': result.release_date,
                    'poster_path': result.poster_path,
                    'vote_average': result.vote_average
                }
                movies.append(movie_info)
                print(f"검색 결과 영화: {result.title}, ID: {result.id}")  # 디버깅용
            except Exception as e:
                print(f"영화 정보 추출 실패: {e}")
                continue
        
        context = {
            'query': query,
            'results': movies,
            'unread_messages': unread_messages
        }
    else:
        context = {'unread_messages': unread_messages}
    return render(request, 'main/base.html', context)

def blog(request):
    search_query = request.GET.get('search', '')
    category_query = request.GET.get('category', '')
    sort_query = request.GET.get('sort', 'latest')  # 기본 정렬 기준은 최신순

    # 기본 쿼리셋
    posts = Post.objects.all()

    # 검색어 필터링
    if search_query:
        posts = posts.filter(title__icontains=search_query)

    # 카테고리 필터링
    if category_query:
        posts = posts.filter(category__icontains=category_query)

    # 정렬
    if sort_query == 'likes':
        posts = posts.order_by('-likes')
    elif sort_query == 'comments':
        posts = posts.annotate(comment_count=Count('comments')).order_by('-comment_count')
    else:  # latest
        posts = posts.order_by('-created_at')

    # 카테고리 목록 가져오기
    categories = Post.objects.values_list('category', flat=True).distinct()

    # 페이지네이션
    paginator = Paginator(posts, 20)  # 한 페이지당 20개
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'main/blog.html', {
        'posts': page_obj,
        'search_query': search_query,
        'category_query': category_query,
        'sort_query': sort_query,
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
            post = form.save(commit=False)
            post.author = request.user
            
            # 세션에서 포스터 URL 가져오기
            poster_url = request.session.get('poster_url')
            if poster_url:
                try:
                    import requests
                    from django.core.files.base import ContentFile
                    from django.utils.text import slugify
                    from io import BytesIO
                    from PIL import Image
                    
                    # 포스터 이미지 다운로드
                    response = requests.get(poster_url)
                    if response.status_code == 200:
                        # 이미지 파일명 생성
                        filename = f"{slugify(post.title)}.jpg"
                        
                        # 이미지 처리
                        img = Image.open(BytesIO(response.content))
                        img_io = BytesIO()
                        img.save(img_io, format='JPEG', quality=85)
                        img_io.seek(0)
                        
                        # 게시물에 이미지 저장
                        post.image.save(filename, ContentFile(img_io.read()), save=False)
                        
                        # 세션에서 포스터 URL 제거
                        if 'poster_url' in request.session:
                            del request.session['poster_url']
                except Exception as e:
                    print(f"포스터 다운로드 실패: {e}")
            
            post.save()
            print(f"게시글 생성 성공: {post.title}")  # 디버깅용
            return redirect('blog')
        else:
            print(f"폼 유효성 검사 실패: {form.errors}")  # 디버깅용
    else:
        # URL 파라미터에서 영화 정보 가져오기
        movie_id = request.GET.get('movie_id')
        title = request.GET.get('title')
        poster_path = request.GET.get('poster')
        
        initial_data = {}
        if title:
            initial_data['title'] = f'[리뷰] {title}'
        
        form = PostForm(initial=initial_data)
        
        # 포스터 URL을 세션에 저장
        if poster_path:
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            request.session['poster_url'] = poster_url
    
    return render(request, 'main/post_new.html', {
        'form': form,
        'poster_url': request.session.get('poster_url', None)
    })
    
def lobby_view(request):
    return render(request, 'main/lobby.html')

@login_required
def chat_view(request, room_name):
    messages = Message.objects.filter(room_name=room_name)
    return render(request, 'main/chat.html', {
        'room_name': room_name,
        'messages': messages
    })

def movie_list(request):
    query = request.GET.get('q', '')
    if query:
        tmdb = TMDb()
        tmdb.api_key = settings.TMDB_API_KEY
        tmdb.language = 'ko'
        
        movie = Movie()
        search_results = movie.search(query)
        
        # 검색 결과에서 영화 정보 추출
        movies = []
        for result in search_results:
            try:
                movie_info = {
                    'id': result.id,
                    'title': result.title,
                    'overview': result.overview,
                    'release_date': result.release_date,
                    'poster_path': result.poster_path,
                    'vote_average': result.vote_average
                }
                movies.append(movie_info)
                print(f"검색 결과 영화: {result.title}, ID: {result.id}")  # 디버깅용
            except Exception as e:
                print(f"영화 정보 추출 실패: {e}")
                continue
        
        context = {
            'query': query,
            'results': movies
        }
        return render(request, 'main/movie_list.html', context)
    else:
        tmdb = TMDb()
        tmdb.api_key = settings.TMDB_API_KEY
        tmdb.language = 'ko'
        
        discover = Discover()
        # 모든 영화 목록 가져오기
        all_movies = []
        for i in range(1, 6):  # 최대 5페이지까지 가져오기
            try:
                page = discover.discover_movies({
                    'sort_by': 'release_date.desc',  # 개봉일 기준 내림차순 정렬
                    'page': i,
                    'include_adult': True,  # 성인 영화 포함
                    'include_video': True,  # 비디오 포함
                    'language': 'ko',  # 한국어
                    'region': 'KR',  # 한국 지역
                    'primary_release_date.lte': datetime.now().strftime('%Y-%m-%d')  # 현재 날짜 이전에 개봉한 영화만
                })
                print(f"페이지 {i}에서 가져온 영화 수: {len(page)}")  # 디버깅용
                print(f"페이지 {i}의 첫 번째 영화: {page[0].title if page else '없음'}")  # 디버깅용
                # 개봉일이 지난 영화만 필터링
                for movie in page:
                    try:
                        movie_info = {
                            'id': movie.id,
                            'title': movie.title,
                            'overview': movie.overview,
                            'release_date': movie.release_date,
                            'poster_path': movie.poster_path,
                            'vote_average': movie.vote_average
                        }
                        if movie.release_date and movie.release_date <= datetime.now().strftime('%Y-%m-%d'):
                            all_movies.append(movie_info)
                            print(f"영화: {movie.title}, ID: {movie.id}")  # 디버깅용
                    except Exception as e:
                        print(f"영화 정보 추출 실패: {e}")
                        continue
            except Exception as e:
                print(f"페이지 {i} 가져오기 실패: {e}")
                continue
        
        print(f"전체 영화 수: {len(all_movies)}")  # 디버깅용
        # 개봉일 기준으로 정렬 (최신순)
        all_movies.sort(key=lambda x: x['release_date'] if x['release_date'] else '', reverse=True)
        
        # 페이지네이션 설정
        paginator = Paginator(all_movies, 21)  # 한 페이지당 20개
        page_number = request.GET.get('page', 1)  # 기본값 1로 설정
        try:
            page_obj = paginator.page(page_number)
            print(f"현재 페이지: {page_obj.number}, 총 페이지 수: {paginator.num_pages}")  # 디버깅용
            print(f"현재 페이지의 영화 수: {len(page_obj.object_list)}")  # 디버깅용
        except (EmptyPage, PageNotAnInteger):
            page_obj = paginator.page(1)
            print("페이지 번호 오류 발생, 첫 페이지로 이동")  # 디버깅용
        
        context = {
            'page_obj': page_obj,
            'today': datetime.now().strftime('%Y-%m-%d')
        }
        return render(request, 'main/movie_list.html', context)

def movie_search(request):
    query = request.GET.get('q', '')
    if query:
        tmdb = TMDb()
        tmdb.api_key = settings.TMDB_API_KEY
        tmdb.language = 'ko'
        
        movie = Movie()
        search_results = movie.search(query)
        
        # 검색 결과에서 영화 정보 추출
        movies = []
        for result in search_results:
            try:
                movie_info = {
                    'id': result.id,
                    'title': result.title,
                    'overview': result.overview,
                    'release_date': result.release_date,
                    'poster_path': result.poster_path,
                    'vote_average': result.vote_average
                }
                movies.append(movie_info)
                print(f"검색 결과 영화: {result.title}, ID: {result.id}")  # 디버깅용
            except Exception as e:
                print(f"영화 정보 추출 실패: {e}")
                continue
        
        context = {
            'query': query,
            'results': movies
        }
    else:
        context = {}
    return render(request, 'main/movie_search.html', context)

def popular_movies(request):
    query = request.GET.get('q', '')
    if query:
        tmdb = TMDb()
        tmdb.api_key = settings.TMDB_API_KEY
        tmdb.language = 'ko'
        
        movie = Movie()
        search_results = movie.search(query)
        
        # 검색 결과에서 영화 정보 추출
        movies = []
        for result in search_results:
            try:
                movie_info = {
                    'id': result.id,
                    'title': result.title,
                    'overview': result.overview,
                    'release_date': result.release_date,
                    'poster_path': result.poster_path,
                    'vote_average': result.vote_average
                }
                movies.append(movie_info)
                print(f"검색 결과 영화: {result.title}, ID: {result.id}")  # 디버깅용
            except Exception as e:
                print(f"영화 정보 추출 실패: {e}")
                continue
        
        context = {
            'query': query,
            'results': movies
        }
        return render(request, 'main/popular_movies.html', context)
    else:
        tmdb = TMDb()
        tmdb.api_key = settings.TMDB_API_KEY
        tmdb.language = 'ko'
        
        movie = Movie()
        popular = movie.popular()
        
        # 결과를 리스트로 변환
        popular_list = []
        for movie in popular:
            try:
                movie_info = {
                    'id': movie.id,
                    'title': movie.title,
                    'overview': movie.overview,
                    'release_date': movie.release_date,
                    'poster_path': movie.poster_path,
                    'vote_average': movie.vote_average
                }
                popular_list.append(movie_info)
                print(f"인기 영화: {movie.title}, ID: {movie.id}")  # 디버깅용
            except Exception as e:
                print(f"영화 정보 추출 실패: {e}")
                continue
        
        # 페이지네이션
        paginator = Paginator(popular_list, 20)  # 한 페이지당 20개
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj
        }
        return render(request, 'main/popular_movies.html', context)

def movie_detail(request, movie_id):
    movie = Movie()
    movie_details = movie.details(movie_id)
    
    # 영화 정보를 데이터베이스에 저장 (선택적)
    MovieModel.objects.update_or_create(
        tmdb_id=movie_details.id,
        defaults={
            'title': movie_details.title,
            'overview': movie_details.overview,
            'release_date': movie_details.release_date if movie_details.release_date else None,  # 개봉일이 비어있으면 None으로 설정
            'poster_path': movie_details.poster_path if movie_details.poster_path else '',  # 포스터 경로가 비어있으면 빈 문자열로 설정
            'vote_average': movie_details.vote_average
        }
    )
    
    context = {
        'movie': movie_details
    }
    return render(request, 'main/movie_detail.html', context)


