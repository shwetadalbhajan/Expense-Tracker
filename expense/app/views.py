import logging
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
import io
from django.shortcuts import render, HttpResponse
from datetime import datetime
from django.template.loader import get_template, render_to_string
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from xhtml2pdf import pisa
from .models import *
from .charts import *

def landing(request):
    return render(request, 'landing.html')

User = get_user_model()

def register(request):
    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        phone = request.POST['phone']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        # Validation
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already in use.")
            return redirect('register')
        if User.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number is already in use.")
            return redirect('register')
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        # Create User
        user = User.objects.create_user(
            username=email,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            password=password,
        )
        user.save()
        messages.success(request, "Registration successful! Please log in.")
        return redirect('login')
    return render(request, 'register.html')

def login_page(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid email or password.")
            return redirect('login')
    return render(request, 'login.html')

@login_required
def dashboard(request):
    # Calculate balance (income - expense)
    total_income = Income.objects.filter(user=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = Expense.objects.filter(user=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
    balance = total_income - total_expense

    # Get recent transactions
    recent_incomes = Income.objects.filter(user=request.user).order_by('-date')[:5]
    recent_expenses = Expense.objects.filter(user=request.user).order_by('-date')[:5]

    # Generate charts
    expense_chart = generate_expense_chart(request.user)
    monthly_chart = generate_monthly_comparison_chart(request.user)
    daily_chart = generate_daily_spending_chart(request.user)

    return render(request, 'dashboard.html', {
        'balance': balance,
        'total_income': total_income,
        'total_expense': total_expense,
        'recent_incomes': recent_incomes,
        'recent_expenses': recent_expenses,
        'expense_chart': expense_chart,
        'monthly_chart': monthly_chart,
        'daily_chart': daily_chart,
    })

@login_required
def add_transaction(request):
    if request.method == 'POST':
        transaction_type = request.POST.get('type')
        amount = request.POST.get('amount')
        date = request.POST.get('date')

        if transaction_type == 'income':
            source = request.POST.get('source')
            Income.objects.create(user=request.user, amount=amount, source=source, date=date)
            messages.success(request, "Income added Successfully")
        elif transaction_type == 'expense':
            category = request.POST.get('category')
            Expense.objects.create(user=request.user, amount=amount, category=category, date=date)
            messages.success(request,"Expense added Successfully")

        return redirect('transaction')
    return render(request, 'transaction.html')

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%b. %d, %Y').date()
    except ValueError:
        return None  # Return None if the date is not in the correct format

def transactions_view(request):
    if request.method == "POST":
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        user = request.user  # Assuming user is logged in

        # Convert string to datetime for filtering
        from_date = parse_date(from_date) if from_date else None
        to_date = parse_date(to_date) if to_date else None

        # Filter transactions
        income_transactions = Income.objects.filter(user=user)
        expense_transactions = Expense.objects.filter(user=user)

        if from_date:
            income_transactions = income_transactions.filter(date__gte=from_date)
            expense_transactions = expense_transactions.filter(date__gte=from_date)

        if to_date:
            income_transactions = income_transactions.filter(date__lte=to_date)
            expense_transactions = expense_transactions.filter(date__lte=to_date)

        # Combine income and expense transactions into one list and sort by date
        all_transactions = list(income_transactions) + list(expense_transactions)
        all_transactions.sort(key=lambda x: x.date)  # Sort by date

        # Add model name to each transaction for the template
        for transaction in all_transactions:
            transaction.model_name = transaction.__class__.__name__  # Add model name (Income or Expense)

        return render(request, 'filter_transactions.html',
                      {'transactions': all_transactions, 'from_date': from_date, 'to_date': to_date})

    return render(request, 'filter_transactions.html')


def download_pdf(request):
    # Fetch from_date and to_date from the GET request
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    user = request.user  # Assuming user is logged in

    # If from_date or to_date is provided, convert to date format
    from_date = parse_date(from_date) if from_date else None
    to_date = parse_date(to_date) if to_date else None

    # Filter transactions based on date range and user
    income_transactions = Income.objects.filter(user=user)
    expense_transactions = Expense.objects.filter(user=user)

    if from_date:
        income_transactions = income_transactions.filter(date__gte=from_date)
        expense_transactions = expense_transactions.filter(date__gte=from_date)

    if to_date:
        income_transactions = income_transactions.filter(date__lte=to_date)
        expense_transactions = expense_transactions.filter(date__lte=to_date)

    # Combine income and expense transactions into one list and sort by date
    all_transactions = list(income_transactions) + list(expense_transactions)
    all_transactions.sort(key=lambda x: x.date)

    # If there are no transactions, return a message
    if not all_transactions:
        return HttpResponse("No transactions found for the selected date range.", status=404)

    # Create a response object with content-type as PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="transactions.pdf"'

    # Create PDF canvas
    p = canvas.Canvas(response, pagesize=letter)

    # Set title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 750, "Transactions")

    # Set table headers and adjust positions for the table
    p.setFont("Helvetica-Bold", 12)
    p.setFillColor(colors.darkgreen)  # Set background color for headers
    p.rect(50, 710, 500, 20, fill=1)  # Create header background
    p.setFillColor(colors.white)  # Reset color for text
    p.drawString(60, 715, "Date")
    p.drawString(180, 715, "Type")
    p.drawString(300, 715, "Source/Category")
    p.drawString(450, 715, "Amount")

    # Set table row data
    y_position = 690  # Start below the headers
    for transaction in all_transactions:
        # Get source for income and category for expense
        source_or_category = transaction.source if isinstance(transaction, Income) else transaction.category

        # Set alternating row background colors
        if y_position % 40 == 0:  # Alternate rows background color
            p.setFillColor(colors.whitesmoke)
            p.rect(50, y_position - 10, 500, 20, fill=1)
        else:
            p.setFillColor(colors.white)
            p.rect(50, y_position - 10, 500, 20, fill=1)

        # Set row text color and content
        p.setFillColor(colors.black)
        p.drawString(60, y_position, str(transaction.date))
        p.drawString(180, y_position, "Income" if isinstance(transaction, Income) else "Expense")
        p.drawString(300, y_position, source_or_category)
        p.drawString(450, y_position, f"{transaction.amount:.2f}")

        # Draw borders around each cell for clarity
        p.setStrokeColor(colors.black)
        p.rect(50, y_position - 10, 500, 20)  # Border for each row

        # Move to the next row
        y_position -= 20

        # Prevent going off the page by adding new page if needed
        if y_position < 100:
            p.showPage()
            p.setFont("Helvetica-Bold", 16)
            p.drawString(200, 750, "Transactions")
            p.setFont("Helvetica-Bold", 12)
            p.setFillColor(colors.darkgreen)
            p.rect(50, 710, 500, 20, fill=1)
            p.setFillColor(colors.white)
            p.drawString(60, 715, "Date")
            p.drawString(180, 715, "Type")
            p.drawString(300, 715, "Source/Category")
            p.drawString(450, 715, "Amount")
            y_position = 690  # Reset y_position for new page

    # Save the PDF and return it in the response
    p.showPage()
    p.save()

    return response

@login_required
def logout_user(request):
    logout(request)
    return redirect('login')