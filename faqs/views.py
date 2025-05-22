# In your app's views.py file
from django.shortcuts import render

def faqs_view(request):
    return render(request, 'faqs.html')