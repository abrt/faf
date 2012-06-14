# -*- coding: utf-8 -*-
from django.utils.encoding import smart_unicode
from django.core.urlresolvers import reverse, NoReverseMatch

class MenuItem:
    """
    Taken from Kobo.  Extended to support placeholder items.
    Basic menu item - every menuitem can have submenu collections of
    these. Only main menu is special instance of Menu class.
    """
    def __init__(self, title, url, acl_groups=None, acl_perms=None,
            placeholder=False, menu=None, on_right=False):
        self.title = smart_unicode(title)

        self._url = url

        self.on_right = on_right
        self.acl_groups = acl_groups and set(acl_groups) or set()
        self.acl_perms = acl_perms and set(acl_perms) or set()
        self.main_menu = None
        self.parent_menu = None
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
        if not self._url:
            return ''

        try:
            return reverse(self._url)
        except NoReverseMatch:
            return reverse(self._url, args=[42])

    @property
    def items(self):
        return [i for i in self.submenu_list if i.visible and
            not i.placeholder]

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
                    self.main_menu.acl_perms[perm] = \
                        self.main_menu.user.has_perm(perm)
                if self.main_menu.acl_perms[perm]:
                    return True
            return False

        return True

class MainMenu(MenuItem):
    """
    Taken from kobo.
    """

    def __init__(self, menu):
        MenuItem.__init__(self, "ROOT_MENU", "", menu=menu)
        self.user = None
        self.path = ""
        self.path_info = ""
        self.cached_menuitems = []
        self.activeItem = None # reference to active menu

        # set main_menu references, compute menu depth
        self.setup_menu_tree(self)

    def __getattr__(self, name):
        # get specified submenu level in active menu
        if not name.startswith("level"):
            raise AttributeError("'%s' object has no attribute '%s'"
                % (self.__class__.__name__, name))

        try:
            level = int(name[5:])
        except ValueError:
            raise AttributeError("'%s' object has no attribute '%s'"
                % (self.__class__.__name__, name))

        if level not in range(1, self.depth + 1):
            raise AttributeError("'%s' object has no attribute '%s'"
                % (self.__class__.__name__, name))

        if self.activeItem is None:
            return None

        if self.activeItem.depth < level:
            raise AttributeError("'%s' object has no attribute '%s'"
            % (self.__class__.__name__, name))

        menu = self.activeItem
        while menu.depth > level:
            menu = menu.parent_menu
        return menu

    def setup(self, request):
        self.user = request.user
        self.path = request.path
        self.path_info = request.path_info
        self.acl_groups = set([i.name for i in
            request.user.groups.all().only("name")])
        self.acl_perms = {}
        self.find_active_menu()
        return self

    def find_active_menu(self):
        split = self.path.split('/')
        last = '*'
        if len(split) > 1:
            last = split[-2]

        items = self.cached_menuitems
        if last.isdigit():
            for i in items:
                i.url = i.url.replace('42', last)

        matches = [i for i in items if i.visible and
            i.url and (self.path.startswith(i.url) or
            self.path_info.startswith(i.url))]
        if not matches:
            return None

        if last.isdigit():
            for i in items:
                i.url = i.url.replace(last, '42')

        # find the longest menu match
        matches.sort(key=len, reverse=True)
        found = matches[0]
        if self.activeItem:
            # reset cached active path
            self.activeItem.set_active(False)
        found.set_active(True)
        self.activeItem = found

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
        MenuItem("Summary", "pyfaf.hub.summary.views.summary"),
        MenuItem("Problems", "pyfaf.hub.problems.views.hot", menu=(
            MenuItem("Hot Problems", "pyfaf.hub.problems.views.hot"),
            MenuItem("Long-term Problems",
                "pyfaf.hub.problems.views.longterm"),
            MenuItem("Problem", "pyfaf.hub.problems.views.summary",
                placeholder=True),
            )),
        MenuItem("Reports", "pyfaf.hub.reports.views.index", menu=(
            MenuItem("Overview", "pyfaf.hub.reports.views.index"),
            MenuItem("List", "pyfaf.hub.reports.views.listing"),
            MenuItem("New", "pyfaf.hub.reports.views.new", on_right=True),
            MenuItem("Report", "pyfaf.hub.reports.views.item",
                placeholder=True),
            )),
        MenuItem("Status", "pyfaf.hub.status.views.index", menu=(
            MenuItem("Overview", "pyfaf.hub.status.views.index"),
            MenuItem("Builds and Packages", "pyfaf.hub.status.views.builds"),
            MenuItem("LLVM Bitcode", "pyfaf.hub.status.views.llvm"),
            MenuItem("All Tasks", "task/index"),
            MenuItem("Running Tasks", "task/running"),
            MenuItem("Finished Tasks", "task/finished"),
            MenuItem("Workers", "worker/list"),
            MenuItem("Arches", "arch/list"),
            MenuItem("Channels", "channel/list"),
            MenuItem("Users", "user/list"),
            )),
        )

mainMenu = MainMenu(menu)
