from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('register/', views.register, name='register'),
    path('login/', views.login_page, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_user, name='logout'),
    path('transaction/', views.add_transaction, name='transaction'),
    path("filter-transactions/", views.transactions_view, name="filter_transactions"),
path('download_pdf/', views.download_pdf, name='download_pdf'),
]
