class FakeArgs(list):
    def use_binary(self, path):
        self[0] = path

    def add_unique(self, args):
        if type(args) is str:
            args = [args]
        elif not type(args) is list:
            raise ValueError("argument must either be str or list")

        for arg in args:
            if not type(arg) is str:
                continue

            if not arg in self:
                self.append(arg)

    def remove_all(self, args):
        if type(args) is str:
            args = [args]
        elif not type(args) is list:
            raise ValueError("argument must either be str or list")

        for arg in args:
            if not type(arg) is str:
                continue

            while arg in self:
                self.remove(arg)

    def remove_regex(self, regex):
        # need to copy the list
        # it is not a good idea to iterate and remove at the same time
        copy = list(self)
        for arg in copy:
            if regex.match(arg):
                self.remove(arg)
