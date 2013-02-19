from django import forms

class NewDumpDirForm(forms.Form):
    file = forms.FileField(label='Dump dir archive')
