import xmlrpclib
import pickle
import datetime

class RpcRecord(object):
    """
    Recorded responses from XML-RPC server.
    """
    def __init__(self, filename=None):
        if filename:
            with open(filename, 'r') as fh:
                self.items = pickle.load(fh)
        else:
            self.items = []

    def get(self, method, args, exc=True):
        for (m, a, r) in self.items:
            if (method, args) == (m, a):
                return r
        else:
            if exc:
                raise KeyError, ("Call to %s with arguments %s not recorded" % (method, args))
            else:
                return None

    def record(self, method, args, result):
        saved = self.get(method, args, exc=False)
        if saved not in (result, None):
            raise KeyError, ("Previous call to %s%s returned %s, current returned %s"
                                % (method, args, saved, result))
        self.items.append((method, args, result))

    def save(self, filename):
        with open(filename, 'w') as fh:
            pickle.dump(self.items, fh)

# Following code borrowed from python std. lib's xmlrpclib.py
# http://svn.python.org/projects/python/trunk/Lib/xmlrpclib.py
class _Method:
    # some magic to bind an XML-RPC method to an RPC server.
    # supports "nested" methods (e.g. examples.getStateName)
    def __init__(self, send, name):
        self.__send = send
        self.__name = name
    def __getattr__(self, name):
        return _Method(self.__send, self.__name + [name])
    def __call__(self, *args):
        return self.__send(self.__name, args)

class XmlRpcRecorder:
    """
    Records communication between xmlrpclib proxy and XML-RPC server. Result
    can be saved and reused in XmlRpcPlayer.
    """
    def __init__(self, proxy):
        # method -> args -> response
        self.__recorded = RpcRecord()
        self.__proxy = proxy

    def __request(self, name, args):
        #print "method %s called with args %s" % (str(name), str(args))
        dotted_name = '.'.join(name)

        # pass the call to the actual xmlrpc proxy
        cur = self.__proxy
        for n in name:
            cur = cur.__getattr__(n)

        try:
            returned = cur.__call__(*args)
        except xmlrpclib.Fault as e:
            # store exceptions too
            returned = e

        self.__recorded.record(dotted_name, args, returned)
        #print "\twith the result %s" % returned

        if isinstance(returned, xmlrpclib.Fault):
            raise returned
        else:
            return returned

    def __save_record(self, filename):
        self.__recorded.save(filename)

    def __getattr__(self, name):
        if name == 'save_record':
            return self.__save_record

        return _Method(self.__request, [name])

class XmlRpcPlayer:
    def __init__(self, filename):
        self.__recorded = RpcRecord(filename)

    def __request(self, name, args):
        dotted_name = '.'.join(name)
        saved = self.__recorded.get(dotted_name, args)

        if isinstance(saved, xmlrpclib.Fault):
            raise saved
        else:
            return saved

    def __getattr__(self, name):
        return _Method(self.__request, [name])
