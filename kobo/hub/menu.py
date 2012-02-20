# -*- coding: utf-8 -*-


from kobo.django.menu import MenuItem, include


# Create your menu here.

# Example:
#
# menu = (
#     MenuItem("MenuItem-1", "/url/path/", absolute_url=True, menu=(
#         MenuItem("MenuItem-1.1", "/url/path/1/", absolute_url=True),
#         MenuItem("MenuItem-1.2", "/url/path/2/", absolute_url=True),
#     )),
#     MenuItem("MenuItem-2", "url_label", ("Developers",), ("app.change_data",)),
#     include("project.app.menu"),
#     MenuItem.include("project.another_app.menu"),
# )
#
# In this example is MenuItem-1 and it's submenu submenu tree accessible for anybody.
# MenuItem-2 is only for users in group Developers with specific permission.
# Instead of specifying complete tree in one file, you can use include()
# command in similar way as it is used in urls.py (see third menu item).
# include() function is also a staticmethod of MenuItem class (see fourth menu item).

# Can be specified only once in project-wide menu
# css_active_class = "active_menu"

# Source of example: docstring in kobo/django/menu/__init__.py


menu = (
    MenuItem("Home", "index"),
    MenuItem("Tasks", "task/index", menu=(
        MenuItem("All", "task/index"),
        MenuItem("Running", "task/running"),
        MenuItem("Finished", "task/finished"),
    )),
    MenuItem("Info", "worker/list", menu=(
        include("kobo.hub.menu"),
    )),
)


css_active_class = "active"
