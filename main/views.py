from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, DeleteView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from .models import Post, Comment
from .forms import PostForm, SignUpForm, CommentForm


# Create your views here.
def base(request):
    return render(request, 'main/base.html')

def blog(request):
    postlist = Post.objects.all()
    return render(request, 'main/blog.html', {'postlist': postlist})

class PostDetailView(DetailView):
    model = Post
    template_name = 'main/post_detail.html'
    context_object_name = 'post'

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
    login_url = '/signup/'

class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'account/signup.html'
    success_url = reverse_lazy('base')

class CustomLoginView(LoginView):
    template_name = 'account/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Login'
        return context

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('base')

class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'main/post_new.html'
    success_url = reverse_lazy('blog')
    
    def form_valid(self, form):
        form.instance.author = self.request.user # 현재 로그인한 사용자를 author로 설정
        return super().form_valid(form)

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

