from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10, unique=True)
    REQUIRED_FIELDS = ['username', 'phone']
    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email

class Income(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=100)
    date = models.DateField()

    def __str__(self):
        return f"{self.source}: ₹ {self.amount}"


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Transport', 'Transport'),
        ('Entertainment', 'Entertainment'),
        ('Bills', 'Bills'),
        ('Others', 'Others'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    date = models.DateField()

    def __str__(self):
        return f"{self.category}: ₹ {self.amount}"