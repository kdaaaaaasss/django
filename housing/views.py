from django.shortcuts import render

def index(request):
    return render(request, "housing/index.html")

# Create your views here.
