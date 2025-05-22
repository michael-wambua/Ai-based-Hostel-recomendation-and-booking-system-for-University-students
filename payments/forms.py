from django import forms
from .models import Payment, Invoice


class PaymentForm(forms.ModelForm):
    """Form for students to submit payment information"""
    
    class Meta:
        model = Payment
        fields = ['transaction_code', 'payment_method', 'notes']
        widgets = {
            'transaction_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter transaction code from your payment'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control'
            }, choices=[
                ('Bank Transfer', 'Bank Transfer'),
                ('Mobile Money', 'Mobile Money'),
                ('Cash Deposit', 'Cash Deposit'),
                ('Other', 'Other')
            ]),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Any additional information about your payment',
                'rows': 3
            }),
        }


class PaymentConfirmationForm(forms.Form):
    """Form for landlords to confirm payments"""
    
    confirm = forms.BooleanField(
        label="I confirm that this payment has been received",
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    notes = forms.CharField(
        label="Notes (optional)",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add any notes about this payment'
        })
    )


class InvoiceForm(forms.ModelForm):
    """Form for creating or updating invoices"""
    
    class Meta:
        model = Invoice
        fields = ['amount', 'due_date']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }