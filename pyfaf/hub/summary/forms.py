from django import forms

OS_RELEASE = (
   ("Fedora 17", "Fedora 17"),
   ("Fedora 16", "Fedora 16"),
   ("Fedora 15", "Fedora 15"),
   ("Debian 6.0.4", "Debian 6.0.4 (squeze)"),
   ("Debian 6.0.3", "Debian 6.0.3 (squeze)"),
)


COMPONENTS = (
    ("coreutils", "coreutils"),
    ("stp", "stp"),
    ("firefox", "firefox"),
)

class ChartForm(forms.Form):
   osrelease = forms.ChoiceField(choices=OS_RELEASE,
                                 label="OS",
                                 required=False)
   component = forms.ChoiceField(choices=COMPONENTS,
                                 label="Components")
