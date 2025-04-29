from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Post, Comment, UserProfile

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'category', 'image', 'region']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '리뷰 제목을 입력하세요'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': '영화에 대한 리뷰를 작성하세요', 'rows': 10}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '현재 위치를 입력하세요'}),
        }
        labels = {
            'title': '리뷰 제목',
            'content': '리뷰 내용',
            'category': '영화 장르',
            'image': '포스터 이미지',
            'region': '현재 위치',
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '댓글을 입력하세요...'}),
        }

class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='필수 항목입니다.')
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        } 