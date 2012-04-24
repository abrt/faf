# -*- coding: utf-8 -*-
from django.utils.encoding import smart_unicode
from django.core.urlresolvers import reverse

class MenuItem:
    """
    Taken from Kobo.  Extended to support placeholder items.
    Basic menu item - every menuitem can have submenu collections of
    these. Only main menu is special instance of Menu class.
    """
    def __init__(self, title, url, acl_groups=None, acl_perms=None, absolute_url=False, placeholder=False, menu=None):
        self.title = smart_unicode(title)
        self._url = url
        self._url_is_resolved = absolute_url
        self.absolute_url = absolute_url
        self.acl_groups = acl_groups and set(acl_groups) or set()
        self.acl_perms = acl_perms and set(acl_perms) or set()
        self.main_menu = None
        self.parent_menu = None
        self.alters_data = False
        self.placeholder = placeholder

        self.submenu_list = []
        for i in menu or []:
            if type(i) in (tuple, list):
                self.submenu_list.extend(i)
            else:
                self.submenu_list.append(i)

        self.active = False
        self.depth = 0

    def __len__(self):
        return len(self.url)

    @property
    def url(self):
        if not self._url_is_resolved:
            self._url = reverse(self._url)
        self._url_is_resolved = True
        return self._url

    @property
    def items(self):
        return [i for i in self.submenu_list if i.visible and not i.placeholder]

    def setup_menu_tree(self, mainmenu_obj):
        if mainmenu_obj != self:
            self.main_menu = mainmenu_obj

        actual_depth = self.depth

        if self.submenu_list:
            mainmenu_obj.depth = max(mainmenu_obj.depth, actual_depth + 1)

        for i in self.submenu_list:
            i.parent_menu = self
            i.depth = actual_depth + 1
            i.setup_menu_tree(mainmenu_obj)
            mainmenu_obj.cached_menuitems.append(i)

    def set_active(self, active):
        self.active = active
        if self.parent_menu is not None:
            self.parent_menu.set_active(active)

    @property
    def visible(self):
        # return False if field should be displayed to user
        if self.main_menu.user.is_superuser:
            return True

        if self.acl_groups:
            if self.acl_groups.intersection(self.main_menu.acl_groups):
                return True
            return False

        if self.acl_perms:
            for perm in self.acl_perms:
                if perm not in self.main_menu.acl_perms:
                    self.main_menu.acl_perms[perm] = self.main_menu.user.has_perm(perm)
                if self.main_menu.acl_perms[perm]:
                    return True
            return False

        return True

class MainMenu(MenuItem):
    """
    Taken from kobo.
    """

    def __init__(self, menu, css_active_class=None):
        MenuItem.__init__(self, "ROOT_MENU", "", absolute_url=True, menu=menu)
        self.user = None
        self.path = ""
        self.path_info = ""
        self.cached_menuitems = []
        self.css_active_class = css_active_class or ""
        self.active = None # reference to active menu (overrides MenuItem behavior)

        # set main_menu references, compute menu depth
        self.setup_menu_tree(self)

    def __getattr__(self, name):
        # get specified submenu level in active menu
        if not name.startswith("level"):
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))

        try:
            level = int(name[5:])
        except ValueError:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))

        if level not in range(1, self.depth + 1):
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))

        if not self.active:
            return None

        if self.active.depth < level:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))

        menu = self.active
        while menu.depth > level:
            menu = menu.parent_menu
        return menu

    def setup(self, request):
        self.user = request.user
        self.path = request.path
        self.path_info = request.path_info
        self.acl_groups = set([i.name for i in request.user.groups.all().only("name")])
        self.acl_perms = {}
        self.find_active_menu()
        return self

    def find_active_menu(self):
        matches = [i for i in self.cached_menuitems if i.visible and i.url and (self.path.startswith(i.url) or self.path_info.startswith(i.url))]
        if not matches:
            return None

        # find the longest menu match
        matches.sort(key=len, reverse=True)
        found = matches[0]
        if self.active:
            # reset cached active path
            self.active.set_active(False)
        found.set_active(True)
        self.active = found
        return found

class LazyMenu(object):
    """
    Cached menu object
    """
    def __get__(self, request, obj_type=None):
        if not hasattr(request, "_cached_menu"):
            request._cached_menu = mainMenu.setup(request)
        return request._cached_menu


class MenuMiddleware(object):
    """
    Middleware for menu object.
    """
    def process_request(self, request):
        """
        @summary: Adds menu to request object
        @param request: http request object
        @type request: django.http.HttpRequest
        """
        request.__class__.menu = LazyMenu()

def menu_context_processor(request):
    """
    @summary: Context processor for menu object.
    @param request: http request object
    @type request: django.http.HttpRequest
    """
    return { "menu": request.menu }


menu = (
        MenuItem("Summary", "pyfaf.hub.summary.views.index"),
        MenuItem("Problems", "pyfaf.hub.problems.views.hot", menu=(
            MenuItem("Hot Problems", "pyfaf.hub.problems.views.hot"),
            MenuItem("Long-term Problems", "pyfaf.hub.problems.views.longterm"),
            MenuItem("Problem", "/problems/", absolute_url=True, placeholder=True),
            )),
        MenuItem("Reports", "pyfaf.hub.reports.views.index", menu=(
            MenuItem("Overview", "pyfaf.hub.reports.views.index"),
            MenuItem("List", "pyfaf.hub.reports.views.list"),
            )),
        MenuItem("Status", "pyfaf.hub.status.views.index", menu=(
            MenuItem("Overview", "pyfaf.hub.status.views.index"),
            MenuItem("Builds and Packages", "pyfaf.hub.status.views.builds"),
            MenuItem("LLVM Bitcode", "pyfaf.hub.status.views.llvm"),
            MenuItem("Tasks", "task/index", menu=(
                    MenuItem("All", "task/index"),
                    MenuItem("Running", "task/running"),
                    MenuItem("Finished", "task/finished"),
                    )),
            MenuItem("Kobo", "worker/list", menu=(
                    MenuItem("Arches", "arch/list"),
                    MenuItem("Channels", "channel/list"),
                    MenuItem("Users", "user/list"),
                    MenuItem("Workers", "worker/list"),
                    )),
            )),
        )

mainMenu = MainMenu(menu, css_active_class ="active")
