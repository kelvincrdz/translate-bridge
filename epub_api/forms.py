from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    full_name = forms.CharField(required=False, label="Nome completo")

    class Meta:
        model = User
        fields = ("username", "email", "full_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este email já está em uso.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        full_name = self.cleaned_data.get("full_name")
        if full_name and hasattr(user, "first_name"):
            # Heurística simples: separar primeiro e restante
            parts = full_name.strip().split(" ")
            user.first_name = parts[0]
            if len(parts) > 1 and hasattr(user, "last_name"):
                user.last_name = " ".join(parts[1:])
        if commit:
            user.save()
        return user
