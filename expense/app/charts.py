import matplotlib
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from django.db.models import Sum
from .models import *

# Set matplotlib to work without a display
matplotlib.use('Agg')

def set_chart_style():
    plt.style.use('ggplot')  # Use a clean style
    plt.rcParams['font.size'] = 12  # Set default font size
    plt.rcParams['axes.labelsize'] = 14  # Label size
    plt.rcParams['xtick.labelsize'] = 12  # X-tick label size
    plt.rcParams['ytick.labelsize'] = 12  # Y-tick label size

def generate_expense_chart(user):
    set_chart_style()
    expenses = Expense.objects.filter(user=user).values('category').annotate(total=Sum('amount'))
    categories = [expense['category'] for expense in expenses]
    totals = [expense['total'] for expense in expenses]

    if not categories:
        categories = ['No Data']
        totals = [1]

    plt.pie(totals, labels=categories, autopct='%1.1f%%', startangle=90, colors=plt.cm.Paired.colors)

    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
    buffer.seek(0)
    chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()
    plt.close()  # Close the figure to free memory
    return chart

def generate_monthly_comparison_chart(user):
    set_chart_style()
    from django.db.models.functions import TruncMonth

    incomes = Income.objects.filter(user=user).annotate(month=TruncMonth('date')).values('month').annotate(total=Sum('amount')).order_by('month')
    expenses = Expense.objects.filter(user=user).annotate(month=TruncMonth('date')).values('month').annotate(total=Sum('amount')).order_by('month')

    months = [income['month'].strftime('%B %Y') for income in incomes]
    income_totals = [income['total'] for income in incomes]
    expense_totals = [expense['total'] for expense in expenses]

    if not months:
        months = ['No Data']
        income_totals = [0]
        expense_totals = [0]

    fig, ax = plt.subplots()
    width = 0.35
    x = range(len(months))
    ax.bar(x, income_totals, width, label='Income', color='#1F4529')
    ax.bar([p + width for p in x], expense_totals, width, label='Expense', color='#D91656')

    ax.set_xticks([p + width / 2 for p in x])
    ax.set_xticklabels(months)
    ax.legend()

    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=150)
    buffer.seek(0)
    chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()
    plt.close()
    return chart

def generate_daily_spending_chart(user):
    set_chart_style()
    expenses = Expense.objects.filter(user=user).values('date').annotate(total=Sum('amount')).order_by('date')
    dates = [expense['date'].strftime('%Y-%m-%d') for expense in expenses]
    totals = [expense['total'] for expense in expenses]

    if not dates:
        dates = ['No Data']
        totals = [0]

    fig, ax = plt.subplots()
    ax.plot(dates, totals, marker='o', color='#D91656', label='Expenses')

    ax.set_xlabel('Date', fontsize=14)
    ax.set_ylabel('Amount (₹)', fontsize=14)
    ax.legend()
    ax.grid(True)

    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=150)
    buffer.seek(0)
    chart = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()
    plt.close()
    return chart