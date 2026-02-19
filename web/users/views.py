from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def home_view(request):
    return render(request, 'users/home.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        return render(request, 'users/login.html', {
            'error': 'Usuario o contraseña incorrectos.',
            'username': username,
        })
    return render(request, 'users/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')
